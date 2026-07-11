---
version: alpha
name: "Sprout AI Job Search"
description: "Sprout is an AI-powered job search platform with a clean, light-themed marketing site. The design centers on a deep forest-green brand palette (#0f4c3d, #1f6a5b) contrasted against white and near-white surfaces. Large, weight-varied headlines (Nunito Sans, 44–64px) create strong typographic hierarchy. Pill-shaped CTAs with dark green fills and white text anchor the hero. A soft teal gradient card preview grounds the lower hero. The overall feel is approachable, spacious, and conversion-focused."
colors:
  surface-white: "#ffffff"
  accent-blue: "#4db6ff"
  surface-near-white: "#fdfdfd"
  surface-off-white: "#fafafa"
  teal-tint: "#eaf7f5"
  brand-deep-green: "#0f4c3d"
  brand-mid-green: "#1f6a5b"
  text-disabled: "#a4a7ae"
  text-primary: "#000000"
  text-secondary: "#535862"
  text-tertiary: "#717680"
  border-subtle: "#e9eaeb"
typography:
  hero-headline:
    fontFamily: "Nunito Sans"
    fontSize: "64px"
    fontWeight: "700"
    lineHeight: "68px"
    letterSpacing: "-1.5px"
  display-heading:
    fontFamily: "Nunito Sans"
    fontSize: "44px"
    fontWeight: "600"
    lineHeight: "48px"
    letterSpacing: "-1.5px"
  display-heading-light:
    fontFamily: "Nunito Sans"
    fontSize: "44px"
    fontWeight: "500"
    lineHeight: "48px"
    letterSpacing: "-1.32px"
  section-heading:
    fontFamily: "Nunito Sans"
    fontSize: "24px"
    fontWeight: "600"
    lineHeight: "32px"
    letterSpacing: "-0.3px"
  subheading:
    fontFamily: "Nunito Sans"
    fontSize: "18px"
    fontWeight: "400"
    lineHeight: "26px"
    letterSpacing: "-0.3px"
  body-regular:
    fontFamily: "Nunito Sans"
    fontSize: "16px"
    fontWeight: "400"
    lineHeight: "24px"
  body-bold:
    fontFamily: "Nunito Sans"
    fontSize: "16px"
    fontWeight: "700"
    lineHeight: "24px"
  body-medium:
    fontFamily: "Nunito Sans"
    fontSize: "16px"
    fontWeight: "500"
    lineHeight: "24px"
    letterSpacing: "-0.2px"
  label-regular:
    fontFamily: "Nunito Sans"
    fontSize: "14px"
    fontWeight: "400"
    lineHeight: "20px"
  caption:
    fontFamily: "Nunito Sans"
    fontSize: "12px"
    fontWeight: "400"
    lineHeight: "16px"
    letterSpacing: "-0.16px"
  micro-label:
    fontFamily: "Nunito Sans"
    fontSize: "10px"
    fontWeight: "400"
    lineHeight: "16px"
    letterSpacing: "-0.16px"
rounded:
  radius-sm: "5px"
  radius-md: "8px"
  radius-lg: "12px"
  radius-xl: "16px"
  radius-2xl: "20px"
  radius-pill: "100px"
  radius-full: "50px"
spacing:
  spacing-1: "4px"
  spacing-2: "8px"
  spacing-3: "10px"
  spacing-4: "12px"
  spacing-5: "16px"
  spacing-6: "20px"
  spacing-7: "24px"
  spacing-8: "32px"
  spacing-9: "40px"
  spacing-10: "80px"
---

## Overview

Sprout is an AI-powered job search platform with a clean, light-themed marketing site. The design centers on a deep forest-green brand palette (#0f4c3d, #1f6a5b) contrasted against white and near-white surfaces. Large, weight-varied headlines (Nunito Sans, 44–64px) create strong typographic hierarchy. Pill-shaped CTAs with dark green fills and white text anchor the hero. A soft teal gradient card preview grounds the lower hero. The overall feel is approachable, spacious, and conversion-focused.

**Signature traits:**
- Single-family weight hierarchy: Builds hierarchy from Nunito Sans across 4 weights rather than multiple families.
- Soft, rounded geometry: Generous corner rounding up to 100px.
- Layered elevation: Depth comes from 4 validated shadow tokens.

## Colors

The palette uses 12 validated color tokens across 1 theme profile. Semantic roles stay attached to observed usage so generation agents can choose accents without inventing new color meaning.

**Semantic naming:**
- **action-text** maps to `brand-deep-green`: Role "text" is grounded by usage context "Primary CTA button fill, logo background, key brand accent".
- **surface-primary** maps to `surface-white`: Role "primary" is grounded by usage context "Primary page background, hero section, card surfaces".
- **surface-background** maps to `surface-off-white`: Role "background" is grounded by usage context "Secondary surface, footer background, subtle section fills".
- **content-text** maps to `text-primary`: Role "text" is grounded by usage context "Primary headings, body text, icon fills".

### Primary Brand
- **Surface White** (#ffffff): Primary page background, hero section, card surfaces. Role: primary. {authored: rgb(255, 255, 255), space: rgb, alpha: 0}

### Text Scale
- **Brand Deep Green** (#0f4c3d): Primary CTA button fill, logo background, key brand accent. Role: text. {authored: rgb(15, 76, 61), space: rgb}
- **Brand Mid Green** (#1f6a5b): Secondary links, icon accents, hover states on green elements. Role: text. {authored: rgb(31, 106, 91), space: rgb}
- **Text Disabled** (#a4a7ae): Disabled states, placeholder text, muted metadata. Role: text. {authored: rgb(164, 167, 174), space: rgb}
- **Text Primary** (#000000): Primary headings, body text, icon fills. Role: text. {authored: rgb(0, 0, 0), space: rgb}
- **Text Secondary** (#535862): Body copy, nav labels, secondary descriptive text. Role: text. {authored: rgb(83, 88, 98), space: rgb}
- **Text Tertiary** (#717680): Muted labels, captions, placeholder text. Role: text. {authored: rgb(113, 118, 128), space: rgb}

### Interactive
- **Border Subtle** (#e9eaeb): Dividers, card outlines, input borders. Role: border. {authored: rgb(233, 234, 235), space: rgb}

### Surface & Shadows
- **Accent Blue** (#4db6ff): Highlight accents, AI feature callouts, link decorations. Role: background. {authored: rgb(77, 182, 255), space: rgb}
- **Surface Near-White** (#fdfdfd): Card and panel backgrounds, inner surface fills. Role: background. {authored: rgb(253, 253, 253), space: rgb}
- **Surface Off-White** (#fafafa): Secondary surface, footer background, subtle section fills. Role: background. {authored: rgb(250, 250, 250), space: rgb}
- **Teal Tint** (#eaf7f5): Soft teal gradient hero card background, highlight tints. Role: background. {authored: rgb(234, 247, 245), space: rgb}

## Typography

Typography uses Nunito Sans across extracted hierarchy roles. Keep hierarchy mapped to these token rows before adding decorative type styles.

Uses Nunito Sans throughout for a uniform feel. Weight range spans bold, semi-bold, medium, regular. Sizes range from 10px to 64px.

### Font Roles
- **Headline Font**: Nunito Sans
- **Body Font**: Nunito Sans

### Type Scale Evidence
| Role | Font | Size | Weight | Line Height | Letter Spacing | Stack / Features | Notes |
|------|------|------|--------|-------------|----------------|------------------|-------|
| Primary hero heading — large weight-contrast display text | Nunito Sans | 64px | 700 | 68px | -1.5px | Nunito Sans, Nunito Sans Placeholder, sans-serif | Extracted token |
| Section display headings, major feature titles | Nunito Sans | 44px | 600 | 48px | -1.5px | Nunito Sans, Nunito Sans Placeholder, sans-serif | Extracted token |
| Paired with bold display heading for weight contrast effect | Nunito Sans | 44px | 500 | 48px | -1.32px | Nunito Sans, Nunito Sans Placeholder, sans-serif | Extracted token |
| Sub-section headings, card titles | Nunito Sans | 24px | 600 | 32px | -0.3px | Nunito Sans, Nunito Sans Placeholder, sans-serif | Extracted token |
| Hero subtext, feature descriptions, lead body copy | Nunito Sans | 18px | 400 | 26px | -0.3px | Nunito Sans, Nunito Sans Placeholder, sans-serif | Extracted token |
| Primary body text, nav items, general content | Nunito Sans | 16px | 400 | 24px | normal | Nunito Sans, Nunito Sans Placeholder, sans-serif | Extracted token |
| Emphasized body text, stat callouts, bold labels | Nunito Sans | 16px | 700 | 24px | normal | Nunito Sans, Nunito Sans Placeholder, sans-serif | Extracted token |
| Medium-weight body, button labels, interactive text | Nunito Sans | 16px | 500 | 24px | -0.2px | Nunito Sans, Nunito Sans Placeholder, sans-serif | Extracted token |
| Form labels, metadata, secondary UI labels | Nunito Sans | 14px | 400 | 20px | normal | Nunito Sans, Nunito Sans Placeholder, sans-serif | Extracted token |
| Captions, footnotes, small metadata text | Nunito Sans | 12px | 400 | 16px | -0.16px | Nunito Sans, Nunito Sans Placeholder, sans-serif | Extracted token |
| Micro labels, badge text, tiny UI annotations | Nunito Sans | 10px | 400 | 16px | -0.16px | Nunito Sans, Nunito Sans Placeholder, sans-serif | Extracted token |

## Layout

Responsive system uses 3 breakpoint tier(s): mobile, tablet, desktop.

This system uses a 4px base grid with scale values 4, 8, 10, 12, 16, 20, 24, 32, 40, 80.

### Responsive Strategy
- **mobile (<= 809.98px)**: Constrain layout for small viewports and prioritize vertical stacking.
- **tablet (810-1199.98px)**: Increase spacing and column structure for medium-width viewports.
- **desktop (Unknown)**: Expand layout density and horizontal composition for wide viewports.

### Spacing System
| Token | Value | Px | Notes |
|------|-------|----|-------|
| spacing-1 | 4px | 4 | Extracted spacing token |
| spacing-2 | 8px | 8 | Extracted spacing token |
| spacing-3 | 10px | 10 | Extracted spacing token |
| spacing-4 | 12px | 12 | Extracted spacing token |
| spacing-5 | 16px | 16 | Extracted spacing token |
| spacing-6 | 20px | 20 | Extracted spacing token |
| spacing-7 | 24px | 24 | Extracted spacing token |
| spacing-8 | 32px | 32 | Extracted spacing token |
| spacing-9 | 40px | 40 | Extracted spacing token |
| spacing-10 | 80px | 80 | Extracted spacing token |

## Elevation & Depth

Keep depth flat unless validated shadow or interaction evidence appears in the extraction payload. Do not invent shadows beyond this evidence boundary.

### Shadow Evidence
| Shadow Token | Layers | Details |
|--------------|--------|---------|
| shadow-subtle | 1 | 0px 0px 2px 0px rgba(0, 0, 0, 0.25) |
| shadow-inset-subtle | 1 | 0px -1px 1px 1px rgba(0, 0, 0, 0.02) |
| shadow-elevated | 1 | 0px 2px 50px 0px rgba(0, 0, 0, 0.25) |
| shadow-card | 2 | 0px 1px 6px 0px rgba(0, 0, 0, 0.06) |

### Interaction Signals
| Theme | Signal | Evidence |
|-------|--------|----------|
| Light | outline-color | rgb(0, 0, 0) ; rgb(83, 88, 98) ; rgb(0, 0, 238) |
| Light | outline-width | 3px |
| Light | outline-offset | 0px |
| Light | transform | matrix(1, 0, 0, 1, 5, 5) ; matrix(1, 0, 0, 1, 0, 0) ; matrix(-1, 0, 0, -1, 0, 0) |

## Shapes

Shape language maps directly to rounded tokens. Keep component corners consistent with the role mapping below before introducing bespoke geometry.

### Radius Roles
| Token | Value | Px | Role Mapping |
|------|-------|----|--------------|
| radius-sm | 5px | 5 | Subtle corner |
| radius-md | 8px | 8 | Control corner |
| radius-lg | 12px | 12 | Control corner |
| radius-xl | 16px | 16 | Card corner |
| radius-2xl | 20px | 20 | Card corner |
| radius-full | 50px | 50 | Large surface corner |
| radius-pill | 100px | 100 | Large surface corner |

### Geometry Evidence
| Radius Token | Shape | Units |
|--------------|-------|-------|
| radius-sm | 5px | px |
| radius-md | 8px | px |
| radius-lg | 12px | px |
| radius-xl | 16px | px |
| radius-2xl | 20px | px |
| radius-pill | 100px | px |
| radius-full | 50px | px |

## Components

(none detected)

## Do's and Don'ts

Guardrails protect Single-family weight hierarchy, Soft, rounded geometry, Layered elevation without adding unsupported visual claims.

| Do | Don't |
|----|---------|
| Do maintain consistent spacing using the base grid | Don't make unsupported claims about absent visual features |
| Do maintain WCAG AA contrast ratios (4.5:1 for normal text) | Don't mix rounded and sharp corners in the same view |
| Do use the primary color only for the single most important action per screen |  |
| Do verify evidence before writing new design-system guidance |  |

## Responsive Evidence

### Breakpoints
| Name | Width | Key Changes |
|------|-------|-------------|
| Breakpoint 1 | <= 809px | (max-width: 809px) and (min-width: 0) |
| Breakpoint 2 | <= 809.98px | (max-width: 809.98px) |
| Tablet | 810-1199px | (max-width: 1199px) and (min-width: 810px) |
| Tablet | 810-1199.98px | (min-width: 810px) and (max-width: 1199.98px) |
| Breakpoint 5 | Unknown | print |

## Agent Prompt Guide

### Example Component Prompts
- Create button component using validated primary color role and spacing tokens.
- Create card component with mapped radius role and evidence-backed elevation.
- Create form input component using inferred typography hierarchy and border roles.

### Iteration Guide
1. Start with extracted palette and typography roles only.
2. Map spacing and radius directly from token tables before visual polish.
3. Apply component patterns one section at a time and compare against source intent.
4. Keep elevation claims tied to explicit evidence in output.
5. Iterate with smallest diffs and re-check section hierarchy after each change.
