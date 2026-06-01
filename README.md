# Review-Readiness Triage for Felid Re-ID in Conservation Camera-Trap Images

This repository contains the planning, documentation, rubric design, and future validation workflow for a conservation computer vision research project on pre-Re-ID review-readiness triage.

The project does not develop a new animal Re-ID model. Instead, it evaluates whether felid camera-trap images are reliable enough to enter individual-level Re-ID review.

## Core Research Questions

### Q1: Reliability

Do images labeled as review-ready show more reliable Re-ID behavior than review-limited or unidentifiable images?

### Q2: Trade-off

After filtering low-readiness images, does pairwise false-match risk proxy decrease, and how much potential known matching evidence is lost?

## Data Roles

- CzechLynx: quantitative known-ID validation carrier.
- UWIN/WildTrax Bobcat and Canada Lynx: field motivation and field-readiness stress test.
- Marbled Cat: future Asian conservation application scenario.

## Current Phase

Phase 0: Project Scope Lock  
Phase 1: Data Access and Triage Rubric

## Boundary

This project does not identify individual animals. It evaluates whether images are reliable enough to enter individual-level Re-ID review.