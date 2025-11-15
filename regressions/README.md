

## Overview

This project provides a modular framework for running **regression tests** against Gemini's ability to correctly interpret prompts, invoke the required **tools**, and produce output containing **expected keywords** for a given prompt for validation.

The primary objective is to maintain consistency in the Gemini's prompt comprehension particularly its ability to correctly route a prompt to one of the defined tool actions(eg., cluster-director-mcp).

###  Current Status: Mocked Execution

Since the Gemini API key is not yet integrated, the current script runis in `mock mode`. All prompt evaluations use a controlled simulation function (mock_gemini_response), to validtae and reporting logic locally.
This ensures the test flow, fuzzy-matching logic and reporting pipelines are fully verified before live API integration.


##  Key Features

* **Configuration-Driven:** Prompts, expected outputs, and required tools are defined in a structured `prompts.json` file located under regression/tests/. This file mirrors the centralized prompt list maintained in the shared Google Doc.

* **Tool Inference Test:** Each prompt entry includes the `Tool` column in the JSON to define the expected tool name (e.g., `run_nccl_test`, `list_clusters`). The framework validates that the prompt routes to the correct tool.
* **Fuzzy Keyword Matching:** Uses the `thefuzz` logic to handle small variations in keyword phrasing (eg., "topology" vs "topologies"), providing a more tolerant evaluation approach while maintaining accuracy.
* **Detailed Reporting:** Generates a detailed JSON report for every test with prompt,category and tool.The report includes output samples and a clear PASS?FAIL status and stored in `output.json` file located under regression/reports/.
* **Category Breakdown:** Provides a summary of the total prompts tested within each specific category, useful for measuring test coverage.

##  Project Structure
beacon_regression
├── regression/  
|    ├── tests/  
|       │└── prompts.json # Input file: Defines all prompts, expected keywords, and target tools.
|    ├── reports/ 
|        │└── output.json    # Output file: Detailed PASS/FAIL result for every single test case.
|    ├── scripts/ 
|        │└── regress_cluster_director_mcp.py    # Main regression executor
|        
├── README.md


## Execution Flow
**1) Create a Virtual environment**


```bash
    python3 -m venv venv
    source venv/bin/activate
```

**2) Install Dependencies using `requirements.txt`:**

```bash
    pip install -r requirements.txt
```

**3.) Running the Evaluator**
    
```bash
    python3 regression/script/regress_cluster_director_mcp.py
```

After execution, the final report will be available under 

``` regression/reports/results.csv```


## Next Steps / Enhancements
. Add service account detailes for google doc ingestion.
. Integrate Gemini API for live inference testing.
. Introduce configurable thresholds for fuzzy matching.
. Expand reporting to include tool-level and prompt-type metrics.


**NOTE**
- The current implementation runs fully in Mock mode for validation purposes.
 
