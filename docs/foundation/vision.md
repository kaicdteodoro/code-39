# Vision

`code-39` is a local-first barcode generation tool for Atlântico Gastrobar. Its only job is to produce a reliable, print-ready batch of Code 39 labels for tabs, with numbering rules that are stable and easy to audit.

## Problem

The business needs 500 physical tabs identified from `ATL001` to `ATL500`. Manual generation is error-prone, can create duplicates, and often produces outputs that still need graphic adjustments before being sent to print.

## Users

- Agência digital responsável pela entrega técnica
- Operador técnico do estabelecimento
- Gráfica responsável pela impressão final

## Desired outcomes

- Deterministic generation of the official range `ATL001` to `ATL500`
- Single high-resolution PDF, ready to print
- Clear prevention of accidental duplicate issuance
- Persistent audit trail with timestamp, range, and quantity

## Non-goals

- No TOTS integration or any external system
- No QR Code generation
- No web or mobile interface
- No real-time operational management of tabs
- No checksum digit
