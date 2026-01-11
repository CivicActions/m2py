# API Contracts: Spec 005 - Structured Control Flow Codegen

This directory contains interface contracts for Spec 005.

## Files

- `codegen_contracts.py` - Type signatures for code generation functions
- `analysis_requirements.md` - Required analysis data for codegen

## Usage

These contracts define the interfaces between:
1. Analysis modules → Codegen modules (data flow)
2. Codegen functions → Generated Python (output contracts)

All code generation functions must respect these contracts.
