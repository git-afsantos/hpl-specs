# HPL - The HAROS Property Specification Language

HPL is a minimalistic specification language tailored for behavioural properties of message-based systems.
Although it might be useful in other contexts, it was designed with the message-passing system of the [Robot Operating System](https://www.ros.org/) in mind.
Since properties are message-based, the same language can be used to specify both individual nodes and full applications.

HPL was developed to be an integral part of the [HAROS framework](https://github.com/git-afsantos/haros/).
HAROS is capable of defining and extracting architectural models of ROS systems (the *ROS Computation Graph*).
Such models are, inherently, mostly concerned with the structure of the analysed system.
This language is meant to annotate the architectural models, complementing them with behavioural information.

## What Is In The Box

This repository contains a Python package, and the respective source code, to parse HPL specifications and convert them into *Abstract Syntax Trees* (AST).

## Syntax, Semantics and Use Cases

Check the [documentation](./docs).

## Installing

To install this package, make sure that you have Python 2.7 or greater.
Simply run the command:

```
pip install hpl-specs
```

## Bugs, Questions and Support

Please use the [issue tracker](https://github.com/git-afsantos/hpl-specs/issues).

## Citing

See [CITING](./CITING.md).

## Contributing

See [CONTRIBUTING](./CONTRIBUTING.md).

## Acknowledgment

This work is financed by the ERDF – European Regional Development Fund through the Operational Programme for Competitiveness and Internationalisation - COMPETE 2020 Programme and by National Funds through the Portuguese funding agency, FCT - Fundação para a Ciência e a Tecnologia within project PTDC/CCI-INF/29583/2017 (POCI-01-0145-FEDER-029583).
