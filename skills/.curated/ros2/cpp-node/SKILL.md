---
name: ros2-cpp-node
description: Shared ROS2 node design guidance plus C++ rclcpp implementation patterns. Use when any ROS2 skill is working with node behavior, graph interfaces, publishers, subscribers, services, actions, timers, parameters, lifecycle compatibility, or C++ .cpp/.hpp node code. Other ROS2 skills should load this as the shared node module before making node-related design or code changes.
---

# ROS2 Node Core

Use this skill as the shared node module for ROS2 work. ROS2 packages, launch files, sensors, debugging sessions, and build rules usually orbit one or more nodes, so load this skill when the task touches node responsibilities, graph interfaces, parameters, lifetimes, or lifecycle compatibility.

For C++ implementations, also use the C++ source references below. For Python nodes, use this skill only for shared ROS2 node concepts and follow the `ros2-python-node` skill for rclpy-specific code.

## Workflow

1. Identify the node role and interfaces: publishers, subscriptions, services, clients, actions, timers, parameters, callback groups, or lifecycle compatibility.
2. Keep each node focused on one logical ROS graph responsibility.
3. Preserve existing node names, topic names, service names, action names, parameter names, QoS, remappings, and namespaces unless the user asked to change behavior.
4. Prefer relative graph names inside reusable nodes and let launch files apply namespace and remapping.
5. Keep parameter declaration, validation, and use close together.
6. Avoid blocking callbacks unless the executor and callback groups are designed for it.
7. When `CMakeLists.txt` is needed, load and use the `ros2-cmakelists` skill. Do not edit build rules from this skill alone.

## C++ Implementation

Use this section when the node implementation is C++.

1. Prefer ordinary `rclcpp::Node` subclasses for node ownership.
2. Use `rclcpp::node_interfaces::NodeInterfaces<>` for helper functions, helper classes, or APIs that should accept both `rclcpp::Node` and `rclcpp_lifecycle::LifecycleNode`.
3. Put simple nodes in one `.cpp` file. Add an `.hpp` only when the class is reused, tested separately, or exported from a library.

## Source Files

For `.cpp` node implementation patterns, load [references/cpp-file.md](references/cpp-file.md).

For optional `.hpp` declarations, load [references/hpp-file.md](references/hpp-file.md).

## NodeInterfaces Rule

Use `rclcpp::Node::SharedPtr` only for code that is intentionally tied to `rclcpp::Node`.

Use `rclcpp::node_interfaces::NodeInterfaces<>` when writing helpers that need node base, logging, clock, parameters, topics, services, timers, or graph access without caring whether the caller is a regular or lifecycle node.

Accept `NodeInterfaces<>` by value in small helper APIs and pass node objects as `*node` or `*lifecycle_node`.

## Checks

- Include only the ROS message/service/action headers actually used.
- Store publishers, subscriptions, services, clients, timers, and callbacks as members when their lifetime must match the node.
- Prefer explicit QoS choices for non-trivial topics.
- Keep graph naming, remapping, and namespace behavior compatible with launch files and existing users.
- Run package build and relevant tests after edits.
