# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.9] - 2026-02-24
### Changed
- Increased the search limit from 8 to 50 results in interactive picker.
- Implemented scrolling in the results list, keeping the TUI size identical but allowing users to navigate through all 50 results.

## [0.2.8] - 2026-02-24
### Fixed
- Fixed an issue in `dgw` workspace scanning where cached `tuples` were deserialized from JSON as `lists`, leading to an `AttributeError` when splitting paths. Now handles both correctly.

## [0.2.7] - 2026-02-14
### Added
- Feature updates and stability improvements for the fuzzy finder.
- Included multi-workspace mode `dgw`.
