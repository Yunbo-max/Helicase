<div align="center">

# 🧬 Helicase

### Uncertainty-Guided Supply Chain Knowledge Graph Construction with Autonomous Multi-Agent LLMs

<p align="center">
  <a href="paper/Helicase_preprint.pdf"><img src="https://img.shields.io/badge/📄_Preprint-PDF-red.svg" alt="Preprint"/></a>
  <a href="https://humanlong-supplychain-deepresearch.hf.space/"><img src="https://img.shields.io/badge/🌐_Live_Demo-Hugging%20Face-yellow.svg" alt="Demo"/></a>
  <a href="#license"><img src="https://img.shields.io/badge/Paper-CC--BY--4.0-blue.svg" alt="Paper License"/></a>
  <a href="#code-availability"><img src="https://img.shields.io/badge/Code-Apache--2.0%20(by%20request)-lightgrey.svg" alt="Code License"/></a>
  <a href="#authors"><img src="https://img.shields.io/badge/Status-Under%20Review-orange.svg" alt="Status"/></a>
</p>

<p align="center">
  <b>An agentic multi-agent system that unwinds opaque supply-chain queries,</b><br/>
  <b>autonomously assembling query-specific knowledge graphs with calibrated, per-fact uncertainty.</b>
</p>

<p align="center">
  <a href="https://humanlong-supplychain-deepresearch.hf.space/"><b>🚀 Try the Live Demo</b></a>
  ·
  <a href="paper/Helicase_preprint.pdf"><b>📖 Read the Paper</b></a>
  ·
  <a href="#code-availability"><b>🔑 Request Source Access</b></a>
</p>

</div>

---

## ⚡ Overview

Helicase is named after the biological enzyme that unwinds DNA to expose the information encoded within. Analogously, the Helicase system iteratively *unwinds* opaque supply-chain queries — disentangling ambiguous terminology, latent dependencies, and fragmented evidence across heterogeneous web sources — and progressively assembles them into a structured, uncertainty-annotated knowledge graph.

**Two failure modes Helicase addresses:**

1. 🕸️ **Structural inference under fragmentation.** Questions such as *"Which Tesla components use lithium from Australian mines?"* have no answer in any single document. The answer must be synthesised by traversing multi-hop dependencies across heterogeneous, low-visibility public web sources.
2. 🎯 **Calibrated uncertainty for decisions.** Narrative answers from frontier LLMs cannot be acted on without per-fact confidence estimates that reflect source reliability and cross-source consistency.

---

## 🌐 Live Demo

Try Helicase right now in your browser:

### 🔗 **[humanlong-supplychain-deepresearch.hf.space](https://humanlong-supplychain-deepresearch.hf.space/)**

Type any supply-chain question (e.g., *"What is the primary supplier of potato for McDonald's french fries in the US?"*) and watch the agent decompose the query, search heterogeneous sources, and assemble a knowledge graph with per-fact uncertainty annotations.

---

## 🏗️ System Architecture

<div align="center">

![Helicase architecture](figs/helicase_architecture.png)

*Helicase's helical loop: a planner decomposes the query and assigns work to specialised search, reasoning, and coding agents; each iteration's evidence updates the knowledge graph and its three-layer uncertainty state, which steers the next iteration until convergence.*

</div>

### Four specialised agents

| Agent | Responsibility |
|---|---|
| 🧠 **Planner** | Decomposes the user query into an action set; at every iteration, generates new actions targeted at high-uncertainty regions of the current knowledge graph. |
| 🔍 **Web Search Agent** | Performs multi-query, multi-source evidence retrieval and extraction from HTML pages, PDF reports, tabular records (CSV/Excel), and social-platform signals (Twitter/X, LinkedIn, industry forums). |
| 🧩 **Reasoning Agent** | Synthesises harvested evidence, performs cross-source inference, and identifies which structural updates the new findings warrant. |
| 💻 **Coding Agent** | Translates these decisions into deterministic, auditable JSON mutations on the knowledge graph (create / merge / revise nodes and edges) with fuzzy entity matching to prevent duplicates. |

### Three-layer uncertainty quantification

| Layer | Captures |
|---|---|
| ⚙️ **Action layer** | Reliability of each individual agent execution (LLM-based factual-consensus scoring across $n$ parallel web queries). |
| 🧭 **Trajectory layer** | Whether the system is still discovering new information or repeating prior investigations (cross-iteration redundancy). |
| 🧠 **Memory layer** | A graph-wide confidence measure consolidating all per-fact uncertainties via *multiplicative accumulation*, used as the convergence signal. |

The loop terminates by **stagnation detection**: if memory-layer uncertainty stops decreasing for several consecutive iterations, the system has exhausted its ability to reduce uncertainty through further search.

---

## 📊 SCQA Benchmark

We release **SCQA (Supply Chain Query Assessment)** — the first benchmark designed for agentic supply-chain discovery — alongside the paper.

<div align="center">

![SCQA quadrants](figs/scqa_quadrants.png)

</div>

- 🧪 **80 supply-chain queries** across personal care, food & beverages, and electronics / automotive
- 🎚️ **4 quadrants** combining two orthogonal dimensions:
  - Reasoning complexity (single-hop vs multi-hop)
  - Information visibility (high vs low)
- ✅ Human-verified ground-truth answers; for the hardest quadrant (Q4), additional entity–relationship ground-truth graphs

### Headline Results

| System | Q1 Acc | Q2 F1 | Q3 Acc | Q4 G-F1 | UCE↓ |
|---|---:|---:|---:|---:|---:|
| Claude Opus 4.6 | 0.80 | 0.55 | 0.55 | 0.63 | — |
| GLM-5 | 0.60 | 0.40 | 0.20 | 0.33 | — |
| DeepSeek-V3.2 | 0.40 | 0.48 | 0.15 | 0.27 | — |
| Qwen3-235B | 0.30 | 0.44 | 0.05 | 0.25 | — |
| ReAct (Qwen3-235B) | 0.60 | 0.39 | 0.45 | 0.32 | — |
| ToT (Qwen3-235B) | 0.55 | 0.30 | 0.35 | 0.39 | — |
| 🧬 **Helicase** | **0.95** | **0.85** | **1.00** | **0.85** | **0.25** |

> Helicase is the **only** system producing calibrated uncertainty estimates over both discovered entities and their relationships.

---

## 🔬 Representative Query Trace

<div align="center">

![Tesla lithium case study](figs/case_study_kg.png)

*Knowledge graph constructed by Helicase for Q64: "Which Tesla components use lithium from Australian mines?" 28 nodes, 45 edges, seven tiers, $U_{memory}$ converged from 1.00 to 0.20 over five helical iterations.*

</div>

For the same query, baseline systems recovered only partial fragments — Claude Opus identified some upstream firms but did not reconstruct the refiner tier or Gigafactory allocation; ReAct retrieved mining-industry information but did not trace material flow through to Tesla products.

---

## 📖 Paper

The full preprint is available in this repository:

- 📄 **[Helicase\_preprint.pdf](paper/Helicase_preprint.pdf)** — 22-page manuscript, currently under peer review
- 📝 **[main.tex](paper/main.tex)** — LaTeX source (ICLR style)
- 📚 **[references.bib](paper/references.bib)** — bibliography

> ⚠️ **Status:** Preprint, under review. Not yet peer-reviewed; please cite the preprint accordingly.

### Citation

```bibtex
@misc{long2026helicase,
  title         = {Helicase: Uncertainty-Guided Supply Chain Knowledge Graph
                   Construction with Autonomous Multi-Agent LLMs},
  author        = {Long, Yunbo and Zhao, Haolang and Zheng, Ge and Brintrup, Alexandra},
  year          = {2026},
  note          = {Preprint, under review.},
  howpublished  = {\url{https://humanlong-supplychain-deepresearch.hf.space/}}
}
```

---

## 🔑 Code Availability

The Helicase reference implementation is licensed under **Apache 2.0**. Because the codebase is held privately and not yet released under a permissive MIT-style licence, **we do not publish the source in this repository.** The hosted demo lets external researchers inspect the system's end-to-end behaviour without source access.

### Requesting source access

Researchers, students, and collaborators interested in:

- 📦 The Helicase source code
- 📊 The SCQA benchmark data and evaluation scripts
- 🔧 Extending the framework for derivative research
- 🤝 Academic or commercial collaborations

are warmly invited to get in touch.

<div align="center">

> ### 📬 Contact (corresponding author)
>
> **Yunbo Long**
> Department of Engineering, University of Cambridge
>
> ✉️ **[yl892@cam.ac.uk](mailto:yl892@cam.ac.uk)**

</div>

Please briefly describe your intended use (academic research, reproducibility study, derivative work, commercial pilot, etc.) so the appropriate materials can be shared under the right terms.

---

## 👥 Authors

| Author | Affiliation | Role |
|---|---|---|
| **Yunbo Long** ✉️ | Department of Engineering, University of Cambridge | **Corresponding author** |
| Haolang Zhao | Department of Engineering, University of Cambridge | Co-author |
| Ge Zheng | Department of Engineering, University of Cambridge | Co-author |
| Alexandra Brintrup | Department of Engineering, University of Cambridge & The Alan Turing Institute | Senior author |

---

## 📜 License

| Asset | Licence |
|---|---|
| 📄 Paper text, figures, supplementary documentation (this repository) | [Creative Commons Attribution 4.0 International (CC-BY-4.0)](LICENSE) |
| 💻 Helicase source code (held privately) | [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0) — distribution by request only; see [Requesting source access](#requesting-source-access) |

---

## 🙏 Acknowledgements

We thank the open-source community whose tools and models made Helicase possible, and the supply-chain practitioners who provided domain feedback during benchmark construction.

---

<div align="center">

**[🌐 Live Demo](https://humanlong-supplychain-deepresearch.hf.space/) · [📄 Paper](paper/Helicase_preprint.pdf) · [✉️ Contact](mailto:yl892@cam.ac.uk)**

</div>
