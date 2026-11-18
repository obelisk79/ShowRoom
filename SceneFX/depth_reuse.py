# SPDX-License-Identifier: LGPL-2.1-or-later
"""The view's own depth buffer as the AO depth pass (toggle: AODepthReuse).

The standard pipeline draws the whole model a second time only to learn
the eye depth of every pixel; on heavy models that draw is most of the
effect's cost.  The view has already drawn that depth, so:

1. ``copy_node``, first in the composite (end-of-frame annotation phase,
   after the scene), blits the depth attachment of the framebuffer being
   drawn, multisampled or not, into a depth texture of the same format;
2. a shader turns it into the layout the AO shaders read (r = positive
   eye depth, 0 on the background; gba = eye normal rebuilt from the
   neighbouring depths) at the depth resolution of the quality level;
3. ``bind_node(unit)`` binds that texture where the depth pass would be.

Unlike the separate pass, everything in the depth buffer counts: edges
(drawn slightly in front of their faces), the shadow catcher's ground,
transparent objects that write depth.  A GL failure sets ``failed``; the
next sync then rebuilds the effect with the standard depth pass.
"""
from __future__ import annotations

import contextlib
from typing import Any

from pivy import coin

from SceneFX import gl_util

failed = False
#: GLSL uniforms of the conversion shader
UNIFORMS = ('dt_src', 'dt_srcSize', 'dt_proj')
DEPTH_BITS_FORMATS = {16: 'GL_DEPTH_COMPONENT16', 32: 'GL_DEPTH_COMPONENT32'}

VERTEX = """#version 120
varying vec2 dt_uv;
void main() {
    dt_uv = gl_Vertex.xy * 0.5 + 0.5;
    gl_Position = vec4(gl_Vertex.xy, 0.0, 1.0);
}
"""

FRAGMENT = """#version 120
uniform sampler2D dt_src;    // the copied depth buffer, window depth
uniform vec2 dt_srcSize;
uniform mat4 dt_proj;
varying vec2 dt_uv;

float eyeDepth(vec2 uv) {
    float d = texture2D(dt_src, uv).r;
    if (d >= 1.0) return 0.0;
    float z = d * 2.0 - 1.0;
    return -(dt_proj[3][2] - z * dt_proj[3][3])
           / (z * dt_proj[2][3] - dt_proj[2][2]);
}

vec3 eyePos(vec2 uv, float d) {
    float ze = -d;
    float wc = dt_proj[2][3] * ze + dt_proj[3][3];
    vec2 ndc = uv * 2.0 - 1.0;
    return vec3(
        (ndc.x * wc - dt_proj[2][0] * ze - dt_proj[3][0]) / dt_proj[0][0],
        (ndc.y * wc - dt_proj[2][1] * ze - dt_proj[3][1]) / dt_proj[1][1],
        ze);
}

void main() {
    vec2 texel = 1.0 / dt_srcSize;
    vec2 uv = (floor(dt_uv * dt_srcSize) + 0.5) * texel;
    float d = eyeDepth(uv);
    if (d <= 0.0) { gl_FragColor = vec4(0.0); return; }
    vec3 C = eyePos(uv, d);

    // on each axis the side with the smaller depth step: silhouettes
    // must not bend the normal
    vec2 ul = uv - vec2(texel.x, 0.0), ur = uv + vec2(texel.x, 0.0);
    vec2 ud = uv - vec2(0.0, texel.y), uu = uv + vec2(0.0, texel.y);
    float dl = eyeDepth(ul), dr = eyeDepth(ur);
    float dd = eyeDepth(ud), du = eyeDepth(uu);
    vec3 L = eyePos(ul, dl), R = eyePos(ur, dr);
    vec3 D = eyePos(ud, dd), U = eyePos(uu, du);
    bool right = dr > 0.0 && (dl <= 0.0 || abs(R.z - C.z) < abs(C.z - L.z));
    bool up = du > 0.0 && (dd <= 0.0 || abs(U.z - C.z) < abs(C.z - D.z));
    vec3 n = normalize(cross(right ? R - C : C - L, up ? U - C : C - D));
    if (n.z < 0.0) n = -n;
    gl_FragColor = vec4(d, n);
}
"""


def available() -> bool:
    """Whether depth reuse can run here (says why not, once)."""
    reason = ('disabled after a GL error' if failed
              else gl_util.missing_dependency())
    if reason is not None:
        gl_util.warn_once('reuse', 'depth reuse unavailable (%s)' % reason)
    return reason is None


def _source_format(gl: Any, framebuffer: int) -> int:
    """Internal format matching the depth of ``framebuffer``.

    A depth blit needs identical formats on both sides.
    """
    default = framebuffer == 0
    depth = gl.GL_DEPTH if default else gl.GL_DEPTH_ATTACHMENT
    stencil = gl.GL_STENCIL if default else gl.GL_STENCIL_ATTACHMENT
    gl.glBindFramebuffer(gl.GL_READ_FRAMEBUFFER, framebuffer)

    def attachment(point: int, name: int) -> int:
        return int(gl.glGetFramebufferAttachmentParameteriv(
            gl.GL_READ_FRAMEBUFFER, point, name))

    bits = attachment(depth, gl.GL_FRAMEBUFFER_ATTACHMENT_DEPTH_SIZE)
    kind = attachment(depth, gl.GL_FRAMEBUFFER_ATTACHMENT_COMPONENT_TYPE)
    has_stencil = False
    # querying an attachment the framebuffer lacks is a GL error on some
    # drivers: no stencil then
    with contextlib.suppress(Exception):
        has_stencil = attachment(
            stencil, gl.GL_FRAMEBUFFER_ATTACHMENT_STENCIL_SIZE) > 0
    if kind == gl.GL_FLOAT:
        return int(gl.GL_DEPTH32F_STENCIL8 if has_stencil
                   else gl.GL_DEPTH_COMPONENT32F)
    if has_stencil:
        return int(gl.GL_DEPTH24_STENCIL8)
    return int(getattr(gl, DEPTH_BITS_FORMATS.get(
        bits, 'GL_DEPTH_COMPONENT24')))


class DepthSource:
    """The depth of one AO pipeline, copied from the view each frame."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width            # of the converted texture
        self.height = height
        self.ready = False
        self.source = 0
        self.source_fbo = 0
        self.source_key: tuple[int, int, int] = (0, 0, 0)
        self.output = 0
        self.output_fbo = 0
        self.program = 0
        self.locations: dict[str, int] = {}
        self.valid = False            # output holds this frame's depth
        self.copy_node = coin.SoCallback()
        self.copy_node.setCallback(self._copy, None)

    def bind_node(self, unit: int) -> Any:
        """A node that binds the converted depth to texture ``unit``."""
        node = coin.SoCallback()
        node.setCallback(self._bind, unit)
        return node

    def _create(self, gl: Any) -> None:
        self.output = gl_util.nearest_texture(gl)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA32F, self.width,
                        self.height, 0, gl.GL_RGBA, gl.GL_FLOAT, None)
        self.output_fbo = int(gl.glGenFramebuffers(1))
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.output_fbo)
        gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0,
                                  gl.GL_TEXTURE_2D, self.output, 0)
        if (gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER)
                != gl.GL_FRAMEBUFFER_COMPLETE):
            raise RuntimeError('depth convert framebuffer incomplete')
        self.program = gl_util.program(gl, VERTEX, FRAGMENT)
        self.locations = {name: gl.glGetUniformLocation(self.program, name)
                          for name in UNIFORMS}
        self.source = gl_util.nearest_texture(gl)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_COMPARE_MODE,
                           gl.GL_NONE)
        self.source_fbo = int(gl.glGenFramebuffers(1))
        self.ready = True

    def _resize_source(self, gl: Any, width: int, height: int,
                       internal: int) -> None:
        # the raw entry point: PyOpenGL's array converter has no entry for
        # the packed depth-stencil types and rejects a null data pointer
        from OpenGL.raw.GL.VERSION.GL_1_0 import glTexImage2D
        packed = {gl.GL_DEPTH24_STENCIL8: gl.GL_UNSIGNED_INT_24_8,
                  gl.GL_DEPTH32F_STENCIL8:
                      gl.GL_FLOAT_32_UNSIGNED_INT_24_8_REV}
        kind = packed.get(internal, gl.GL_FLOAT)
        fmt = (gl.GL_DEPTH_STENCIL if internal in packed
               else gl.GL_DEPTH_COMPONENT)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.source)
        glTexImage2D(gl.GL_TEXTURE_2D, 0, internal, width, height, 0, fmt,
                     kind, None)
        gl.glBindFramebuffer(gl.GL_DRAW_FRAMEBUFFER, self.source_fbo)
        point = (gl.GL_DEPTH_STENCIL_ATTACHMENT if internal in packed
                 else gl.GL_DEPTH_ATTACHMENT)
        gl.glFramebufferTexture2D(gl.GL_DRAW_FRAMEBUFFER, point,
                                  gl.GL_TEXTURE_2D, self.source, 0)
        gl.glDrawBuffer(gl.GL_NONE)
        gl.glReadBuffer(gl.GL_NONE)
        if (gl.glCheckFramebufferStatus(gl.GL_DRAW_FRAMEBUFFER)
                != gl.GL_FRAMEBUFFER_COMPLETE):
            raise RuntimeError('depth copy framebuffer incomplete')
        self.source_key = (width, height, internal)

    def _check(self, gl: Any, step: str) -> None:
        error = gl.glGetError()
        if error != gl.GL_NO_ERROR:
            raise RuntimeError('%s failed, GL error 0x%x' % (step, error))

    def _convert(self, gl: Any, drawn: int, viewport: list[int],
                 projection: Any) -> None:
        x, y, width, height = viewport
        if not self.ready:
            self._create(gl)
        internal = _source_format(gl, drawn)
        if self.source_key != (width, height, internal):
            self._resize_source(gl, width, height, internal)
        gl.glBindFramebuffer(gl.GL_READ_FRAMEBUFFER, drawn)
        gl.glBindFramebuffer(gl.GL_DRAW_FRAMEBUFFER, self.source_fbo)
        gl.glDisable(gl.GL_SCISSOR_TEST)
        gl.glBlitFramebuffer(x, y, x + width, y + height, 0, 0, width,
                             height, gl.GL_DEPTH_BUFFER_BIT, gl.GL_NEAREST)
        self._check(gl, 'depth blit')

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.output_fbo)
        gl.glViewport(0, 0, self.width, self.height)
        for capability in (gl.GL_DEPTH_TEST, gl.GL_BLEND, gl.GL_CULL_FACE,
                           gl.GL_STENCIL_TEST):
            gl.glDisable(capability)
        gl.glDepthMask(gl.GL_FALSE)
        gl.glColorMask(True, True, True, True)
        gl.glUseProgram(self.program)
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.source)
        gl.glUniform1i(self.locations['dt_src'], 0)
        gl.glUniform2f(self.locations['dt_srcSize'], width, height)
        gl.glUniformMatrix4fv(self.locations['dt_proj'], 1, gl.GL_FALSE,
                              projection)
        gl_util.draw_quad(gl)
        self._check(gl, 'depth convert')

    def _copy(self, data: Any, action: Any) -> None:
        global failed
        render = coin.SoGLRenderAction.getClassTypeId()
        if failed or not action.isOfType(render):
            return
        gl = gl_util.load()
        gl_util.clear_errors(gl)
        drawn = int(gl.glGetIntegerv(gl.GL_DRAW_FRAMEBUFFER_BINDING))
        viewport = [int(v) for v in gl.glGetIntegerv(gl.GL_VIEWPORT)]
        _, projection = gl_util.matrices(gl)
        try:
            with gl_util.preserved_state(gl):
                self._convert(gl, drawn, viewport, projection)
            self.valid = True
        except Exception as exc:  # noqa: BLE001 - called from Coin's render
            failed = True
            self.valid = False
            gl_util.warn_once('reuse-gl', 'depth reuse disabled (%s)' % exc)

    def _bind(self, unit: int, action: Any) -> None:
        render = coin.SoGLRenderAction.getClassTypeId()
        if self.valid and action.isOfType(render):
            gl_util.bind(gl_util.load(), unit, self.output)
