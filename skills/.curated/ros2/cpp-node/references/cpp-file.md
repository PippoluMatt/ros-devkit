# ROS2 C++ .cpp Node Files

Use this reference when creating or editing a C++ ROS2 node implementation.

## Minimal Node Shape

Prefer this structure for simple executable nodes:

```cpp
#include <chrono>
#include <memory>

#include "rclcpp/rclcpp.hpp"

using namespace std::chrono_literals;

class ExampleNode : public rclcpp::Node
{
public:
  ExampleNode()
  : rclcpp::Node("example_node")
  {
    timer_ = create_wall_timer(500ms, [this]() {
      RCLCPP_INFO(get_logger(), "tick");
    });
  }

private:
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<ExampleNode>());
  rclcpp::shutdown();
  return 0;
}
```

Keep the file self-contained unless the node class needs to be reused from tests or another target.

## NodeInterfaces Helpers

Use `NodeInterfaces<>` when writing code that should accept `rclcpp::Node` and `rclcpp_lifecycle::LifecycleNode`.

```cpp
#include "rclcpp/node_interfaces/node_interfaces.hpp"

using NodeInfoInterfaces = rclcpp::node_interfaces::NodeInterfaces<
  rclcpp::node_interfaces::NodeBaseInterface,
  rclcpp::node_interfaces::NodeLoggingInterface>;

void log_node_name(NodeInfoInterfaces interfaces)
{
  const auto base = interfaces.get_node_base_interface();
  const auto logging = interfaces.get_node_logging_interface();
  RCLCPP_INFO(logging->get_logger(), "Node name: %s", base->get_name());
}
```

Call helper APIs with a node object reference:

```cpp
auto node = std::make_shared<ExampleNode>();
log_node_name(*node);
```

Do not accept `rclcpp::Node::SharedPtr` in reusable helpers unless lifecycle nodes are explicitly out of scope.

## Common Interface Sets

Choose the narrowest set that supports the helper:

```cpp
using LoggingInterfaces = rclcpp::node_interfaces::NodeInterfaces<
  rclcpp::node_interfaces::NodeLoggingInterface>;

using TimerInterfaces = rclcpp::node_interfaces::NodeInterfaces<
  rclcpp::node_interfaces::NodeBaseInterface,
  rclcpp::node_interfaces::NodeTimersInterface,
  rclcpp::node_interfaces::NodeLoggingInterface>;

using ParameterInterfaces = rclcpp::node_interfaces::NodeInterfaces<
  rclcpp::node_interfaces::NodeParametersInterface,
  rclcpp::node_interfaces::NodeLoggingInterface>;
```

Add topic, service, graph, clock, or waitables interfaces only when the helper uses them.

## Publishers and Subscriptions

Store communication objects as members:

```cpp
publisher_ = create_publisher<std_msgs::msg::String>("status", rclcpp::QoS(10));
subscription_ = create_subscription<std_msgs::msg::String>(
  "command",
  rclcpp::QoS(10),
  [this](std_msgs::msg::String::ConstSharedPtr msg) {
    RCLCPP_INFO(get_logger(), "command: %s", msg->data.c_str());
  });
```

Use explicit callback methods when callbacks grow beyond a few lines.

## Parameters

Declare parameters before reading them:

```cpp
declare_parameter<double>("rate_hz", 10.0);
const auto rate_hz = get_parameter("rate_hz").as_double();
```

For runtime parameter changes, validate with an on-set-parameters callback and store the callback handle as a member.

## Editing Existing Nodes

- Preserve existing topic names, parameter names, QoS, and node names unless the user asked to change behavior.
- Keep callback ownership and object lifetimes explicit.
- Prefer small helper functions over new classes for single-use logic.
- If a build file change is required, stop and load `ros2-cmakelists`.
