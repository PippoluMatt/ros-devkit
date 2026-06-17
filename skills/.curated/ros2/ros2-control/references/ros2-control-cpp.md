# ROS2 Control C++ Implementation

The full `.cpp` implementation is intentionally deferred in v1 of this skill.

## v1 Boundary

Generate or patch only the pieces required to make the package structure and plugin registration consistent:

- Header declarations.
- Optional minimal `.cpp` skeleton when explicitly requested.
- `PLUGINLIB_EXPORT_CLASS`.
- Plugin XML.
- Build and manifest wiring.

Do not invent driver communication, joint parsing policy, command limits, lifecycle behavior, or error recovery without user-provided hardware details.

## Minimal Skeleton

When the user explicitly requests a skeleton, create method stubs that compile only after the package-specific include path is correct. Return conservative defaults and leave driver work marked with clear placeholder comments.
