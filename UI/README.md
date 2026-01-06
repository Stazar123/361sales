

run command:

python -m streamlit run ui/app.py

python -m streamlit run ui/app.py

ui/ — Application Layer (Streamlit)
This folder contains the interactive application layer of the project.
Its purpose is to present insights, live status, and actions based on pre-computed data, while keeping all business logic modular, testable, and easy to extend.
The UI is intentionally split into small, responsibility-focused modules so the app can evolve (LTV models, clustering, new product logic) without turning into a monolithic file.
Design Principles
app.py is an orchestrator, not a logic dump
Defines layout, tabs, and user controls
Calls computation + rendering functions
Contains no heavy business logic
Business logic lives outside the UI
Retention rules, due-date logic, benchmarks → isolated and reusable
Aggregations and summaries → separated from visualization
UI components are replaceable
Charts/tables live in dedicated functions
Visual changes do not affect computation logic
This separation allows:
fast iteration on UI
safe refactors of logic
easy addition of LTV, clustering, cohorts, and experimentation
Folder Structure & Responsibilities
ui/
│
├── app.py
├── data_io.py
├── live_logic.py
├── compare_logic.py
├── ui_components.py
└── __init__.py
File-by-File Explanation
app.py — Application Orchestrator
What it does:
Defines page config, sidebar controls, and tabs
Loads data once and passes it downstream
Connects user inputs → logic → UI components
What it must NOT do:
Implement retention logic
Compute metrics inline
Contain long plotting code
If this file grows too large, the next step is to split each tab into its own renderer file.
data_io.py — Data Loading & Normalization
Responsibilities:
Load all required parquet files
Handle column standardization / renaming
Provide cached, validated dataframes
Why it exists:
Ensures a single source of truth for input data
Keeps IO concerns separate from logic and UI
live_logic.py — Core Retention & Status Engine
Responsibilities:
Compute due dates and coverage windows
Apply benchmark logic (quantile / manual)
Assign customer status (ok, due_soon, overdue)
Support both:
single-product computation
all-product computation (for overview & comparison)
This is the most important logic layer.
Future extensions (filters, pitchers, bundles, LTV assumptions) should be added here.
compare_logic.py — Aggregation & Comparison Logic
Responsibilities:
Aggregate customer-level data to product-level metrics
Compute repeat rates, urgency rates, median retention
Prepare data for cross-product comparison views
Why it’s separate from live_logic:
live_logic answers “what is the status?”
compare_logic answers “how do products compare?”
Future LTV summaries and cohort metrics belong here.
ui_components.py — Reusable UI Blocks
Responsibilities:
Render charts and tables
Format benchmark labels and annotations
Encapsulate visualization logic
Rules:
Receives prepared dataframes
Does not compute business logic
Can be swapped or redesigned freely
This makes UI experimentation safe and fast.
__init__.py
Marks ui/ as a Python package so imports like:
from ui.live_logic import compute_live_dynamic
work reliably when running the app.
How the Pieces Work Together
High-level flow:
app.py
Reads sidebar controls
Loads data via data_io
live_logic
Computes customer-level live status
compare_logic
Aggregates metrics for comparison
ui_components
Renders charts and tables
User interacts → app recomputes → UI updates
Running the App
From the repository root:
python -m streamlit run ui/app.py
This ensures the ui package is resolved correctly.
Future Extensions (by design)
This structure is intentionally built to support:
Customer LTV modeling
Product clustering & similarity analysis
Cohort analysis & lifecycle stages
Experimentation with different retention benchmarks
Automated action prioritization
All without rewriting the UI.