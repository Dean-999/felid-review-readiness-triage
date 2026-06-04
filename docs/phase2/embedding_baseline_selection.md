# Embedding Baseline Selection

## Purpose

The embedding baseline provides a fixed measurement signal for Phase 2 validation. It is not the project's final product, and it should not be presented as a new Re-ID model.

## Baseline Selection Criteria

The baseline should be:

- pretrained or otherwise established before this project;
- documented with a stable source, version, and citation;
- usable without training on the CzechLynx pilot;
- deterministic enough to support repeatable measurement;
- compatible with local compute limits;
- appropriate for image-level feature extraction;
- simple to record, rerun, and audit.

Preference should go to a baseline that is easy to reproduce over a more complex model that is difficult to document.

## Why Not Train a New Model

This project evaluates review-readiness triage, not model development.

Training a new model would add confounding factors:

- performance could reflect training choices rather than triage quality;
- the 200-image pilot is too small for robust model-development claims;
- training would shift the project toward Re-ID model creation;
- model tuning could leak information from the validation design into the measurement signal.

Using a fixed pretrained or established embedding model keeps Phase 2 focused on whether triage labels correspond to more reliable known-ID similarity behavior.

## Run Record Fields

When embedding extraction is later authorized, record:

- model name;
- model version;
- model source or repository;
- citation or documentation link;
- preprocessing steps;
- image size;
- crop or resize policy;
- normalization parameters;
- device;
- software versions;
- date run;
- input validation table path;
- pair file path;
- output embedding path;
- operator or script name.

## Forbidden Claims

Do not claim:

- state-of-the-art performance;
- a new Re-ID model;
- model training success;
- deployment-ready animal identification;
- a universal Re-ID threshold;
- final scientific conclusions from embedding scores alone.

Embedding outputs, when produced later, are measurement signals used to evaluate triage readiness.
