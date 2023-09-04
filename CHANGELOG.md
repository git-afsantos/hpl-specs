# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## v1.1.2 - 2023-09-04
### Fixed
- Sanity error when creating some types of predicates that was too strict.

## v1.1.1 - 2023-09-04
### Fixed
- Exception when parsing specifications.

## v1.1.0 - 2023-09-04
### Added
- `hpl` CLI script to test file/property parsing

## v1.0.0 - 2023-08-07
### Changed
- Python 2 is no longer supported.
- Modernized tooling and package structure.
- Improved API in various aspects, with some backward-incompatible changes.
- AST objects are mostly immutable, with available methods to create mutated copies.
- Added a number of attribute validators for AST data types.

## v0.2.3 - 2021-08-27
### Fixed
- Fixed a bug with properties that had complex events such as disjunctions.

## v0.2.2 - 2021-08-06
### Fixed
- `MANIFEST.in` was missing `requirements.txt`, causing an issue when installing with `pip`.

## Added
- More builtin functions to use with `HplFunctionCall`.

## v0.2.1 - 2021-02-08
### Changed
- `HplEventDisjunction` requires unique ROS names for each disjoint event.

### Fixed
- `HplProperty` sanity checks for Requirement pattern.

## v0.2.0 - 2021-02-08
### Added
- Convenience methods in `HplPredicate` to check references to aliases.
- Event disjunctions; e.g., `(a or b) causes c`.
- Convenience methods to duplicate `HplAstObject` instances.
- `logic` module with some convenience, logic-related functions.

