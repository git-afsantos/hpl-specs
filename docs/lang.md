# Language Overview

This document provides an overview of the High-level Property Specification Language (HPL).
Here you may find some [context](#context) and motivation for the language, its [core concepts](#concept) and a few [examples](#in-practice).

## Context

In publisher-subscriber architectures (especially), where there are many-to-many communications, it is common to implement components in such a way that they are independent to some degree -- i.e., nodes should make no assumptions about other nodes in the network.
All application logic should revolve around the *exchanged messages* and the *data* they carry, since these are the main observable actions that nodes take, from the software's perspective.
Consequently, properties about a system (or component) should also focus on the exchanged messages and the relations between messages.

This approach applies naturally to the message-passing nature of middlewares such as the Robot Operating System (ROS).
For instance, an informal property for a mobile robot could state that *"whenever a message is observed on topic* `/bumper` *such that the robot's bumper is pressed, a message on topic* `/stop` *should follow, within 100 milliseconds of the first"*.
Considering this example, and how messages work in ROS, a specification language for ROS systems (such as HPL) must provide a few basic features, namely:

- references to individual resource names (e.g., topics);
- references to message contents (e.g., observing the contents of the `/bumper` message);
- temporal operators and relations (e.g., the message on `/stop` is observed after *and because of* the message on `/bumper`);
- real-time behaviour specifications (e.g., observing a message at most 100 milliseconds after observing another).

## Concept

One of the goals of HPL is to provide a property specification language that is both minimalistic and domain specific, yet readable, easily extensible and similar to existing languages.
Such traits improve the ease of use, lower the barrier to adoption and alleviate the burden of specification in general.
Another way to make specification more straightforward and less error prone is to restrict properties to a set of well-known patterns.

The [property specification patterns](https://matthewbdwyer.github.io/psp/) proposed by Dwyer et al. ([DwyerAC:98](https://dl.acm.org/doi/10.1145/298595.298598), [DwyerAC:99](https://dl.acm.org/doi/10.1145/302405.302672)) have been widely adopted, due to them capturing a large number of interesting real-world scenarios.
Their approach of dividing a property into a combination of predefined scopes and patterns aids in streamlining the specification process, without sacrificing much in terms of expressive power.

The HPL language revolves mostly around the **Absence**, **Existence**, **Precedence** and **Response** patterns.

- *Absence (example):* The robot shall never move faster than 1 m/s.
- *Existence (example):* The robot shall, eventually, move.
- *Precedence (example):* The robot only moves if given a command or trajectory in the previous 5 seconds.
- *Response (example):* Given a command or trajectory, the robot shall start moving within the next 5 seconds.

In addition, it also adopts the **Global**, **After** and **After-Until** scopes.

- *Global:* The pattern always holds, from the moment the system is launched until it is shut down.
- *After:* The pattern holds from the moment a specific event is observed for the *first time*, until the system is shut down.
- *After-Until:* The pattern holds from the moment a specific event is observed for the *first time*, until *either* a second event is observed for the first time *or* the system is shut down (the second event is not mandatory).

Diverging from the original specification patterns, HPL introduces the **Until** scope.

- *Until:* The pattern holds, from the moment the system is launched, until *either* a specific event is observed for the first time *or* the system is shut down (the event is not mandatory).

And the **Prevention** pattern.

- *Prevention (example):* Given a stop command, the robot shall *not* move within the next 5 seconds.

As we can see from the (English) examples given so far, HPL covers some crucial features, in the safety-critical context of cyber-physical systems, that were lacking in Dwyer's original specification patterns.
Namely, properties can address real-time constraints (e.g., *"within the next 5 seconds"*) and message contents directly (e.g., *"move faster than 1 m/s"*).

## In Practice

Scopes and patterns are specified in terms of events, e.g., *"after receiving a message such that &phi;"*, or *"there are no messages such that &phi;"*.
In its simplest form, an event simply requires a *topic name*, under which messages should be observed, for example:

```
/cmd_vel
```

Any message passing through the `/cmd_vel` topic should match the event.
Optionally, an event may be refined with a predicate over the message's data fields, which will act as a sort of filter; only those messages that satisfy the predicate will match the event.
This is how we impose, for instance, ranges of expected values for a certain field:

```
/cmd_vel {linear.x in [0.0 to 1.0]}
```

Finally, predicates may include references to previous messages in the same timeline (depending on the property's scope and pattern).
This way, we have the necessary tools to establish relations between messages and message fields, such as equality and monotonicity.

```
/cmd_vel {linear.x = @teleop.linear.x}
```

To write down a full property, you simply combine events with the appropriate keywords for patterns and scopes.
For example, to state that `linear.x` should *never* go over 1 m/s:

```
globally: no /cmd_vel {linear.x > 1.0}
```

Putting all concepts together, a property basically comes down to the following hierarchichal structure (where dashed lines represent optional elements).

![Concept Diagram](./fig/concept.png?raw=true "Concept Diagram")

For the complete syntax reference, see [Language Syntax](./syntax.md).
