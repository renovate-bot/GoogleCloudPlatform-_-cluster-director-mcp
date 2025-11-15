import json
from typing import Dict, Any, List, Union, Tuple
from thefuzz import fuzz 
from collections import defaultdict
import os


FUZZY_MATCH_THRESHOLD: int = 85         # Minimum score (out of 100) for a keyword to be considered a match
MIN_KEYWORD_MATCH_RATIO: float = 0.85   # Minimum percentage of keywords that must pass the fuzzy check


class TestResult:
    """A structured container for storing the result of a single test step."""
    def __init__(self, item: Dict[str, Any], response: str, is_pass: bool, notes: str):
        self.tool = item.get("Tool", "N/A")
        self.category = item.get("Category", self.tool) 
        self.prompt = item.get("Prompt", "N/A")
        self.expected_keywords = item.get("Expected Output Keywords", [])
        self.response = response
        self.is_pass = is_pass
        self.notes = notes

    def to_dict(self) -> Dict[str, Union[str, bool, List[str]]]:
        """Converts the result object to a dictionary for JSON reporting."""
        return {
            "Prompt": self.prompt,
            "Tool": self.tool,
            "Category": self.category,
            "ExpectedOutputKeywords": self.expected_keywords,
            "GeminiResponse": self.response,
            "Result": "PASS" if self.is_pass else "FAIL"
        }


class GeminiPromptEvaluator:
    """Evaluates prompts against mocked Gemini API responses and checks keyword matches."""
    def __init__(self, input_json_path: str, output_json_path: str):
        self.input_json_path = input_json_path
        self.output_json_path = output_json_path
        self.all_results: List[TestResult] = []

    def _load_json(self) -> List[Dict[str, Any]]:
        """Loads the JSON file containing prompts and expected keywords."""
        try:
            with open(self.input_json_path, "r") as file:
                return json.load(file)
        except FileNotFoundError:
            print(f"FATAL ERROR: Input file not found at path: {self.input_json_path}")
            raise
        except json.JSONDecodeError:
            print(f"FATAL ERROR: Input file is not valid JSON: {self.input_json_path}")
            raise


    def mock_gemini_response(self, prompt: str) -> str:
        """
        Mocks the Gemini API response based on prompt content.
        """
        responses: Dict[str, str] = {
            "nccl": "The NCCL test completed successfully. Result verified and test finished.", 
            "status": "Job status for cluster nadig is a3-megagpu-8g and in europe-west1-c is completed.",
            "default": "The system executed the command successfully. Default response applied."
        }
        
        prompt_lower = prompt.lower()

        if "check the status" in prompt_lower or "check_job_status" in prompt_lower:
             return responses["status"]
        if "nccl" in prompt_lower or "run_nccl_test" in prompt_lower:
            return responses["nccl"]
                
        return responses["default"]

    def _get_match_notes(self, keyword: str, text: str) -> Tuple[bool, str]:
        """Checks fuzzy match silently and returns status/notes."""
        score = fuzz.partial_ratio(keyword.lower(), text.lower())
        
        if score >= FUZZY_MATCH_THRESHOLD:
            return True, f"Keyword matched (Score: {score})"
        else:
            return False, f"Keyword failed (Score: {score} < Threshold: {FUZZY_MATCH_THRESHOLD})"

    def _check_keywords(self, response: str, expected_keywords: List[str]) -> Tuple[bool, str]:
        """Runs the keyword check silently, returning final status and aggregated notes."""
        if not expected_keywords:
            return False, "Error: No expected keywords provided for this test."

        matched_count = 0
        all_notes: List[str] = []
        
        for keyword in expected_keywords:
            is_matched, notes = self._get_match_notes(keyword, response)
            all_notes.append(f"'{keyword}': {notes}")
            if is_matched:
                matched_count += 1
                
        match_ratio = matched_count / len(expected_keywords)
        
        is_pass = match_ratio >= MIN_KEYWORD_MATCH_RATIO
        
        status_line = f"Overall Status: {'PASS' if is_pass else 'FAIL'} | Matched {matched_count}/{len(expected_keywords)} ({match_ratio:.0%} match)."
        detailed_notes = f"{status_line}\nDetails: {'; '.join(all_notes)}"
        
        return is_pass, detailed_notes
        

    def _run_single_test(self, item: Dict[str, Any]) -> TestResult:
        """Runs a single prompt evaluation and returns a TestResult object."""
        prompt = item.get("Prompt", "N/A")

        gemini_response = self.mock_gemini_response(prompt)

        is_pass, notes = self._check_keywords(
            gemini_response, 
            item.get("Expected Output Keywords", [])
        )

        return TestResult(item, gemini_response, is_pass, notes)
    

    def _print_tool_summary(self) -> None:
        "Prints a summary breakdown of tool prompts per tool."
        tool_counts: Dict[str, int] = defaultdict(int)

        for result in self.all_results:
            tool_counts[result.tool] += 1
        
        print("\n --- Tool Wise Prompt Counts ---")

        sorted_tools = sorted(tool_counts.items())
        max_tool_len = max(len(tool) for tool, _ in sorted_tools) if sorted_tools else 0

        for tool, count in sorted_tools:
            print(f" Tool: {tool:<{max_tool_len+4}} | Prompts: {count:>5}")
        print("-" * (max_tool_len + 10))

    def _print_summary_table(self) -> None:
        """Prints the concise, category-wise summary table to the terminal."""
        
        summary: Dict[str, Dict[str, int]] = defaultdict(lambda: {"Total": 0, "PASS": 0, "FAIL": 0})
        
        for result in self.all_results:
            category = result.category
            summary[category]["Total"] += 1
            if result.is_pass:
                summary[category]["PASS"] += 1
            else:
                summary[category]["FAIL"] += 1
        
        grand_total = sum(d["Total"] for d in summary.values())
        grand_pass = sum(d["PASS"] for d in summary.values())
        grand_fail = sum(d["FAIL"] for d in summary.values())
        
        overall_status = "PASS" if grand_fail == 0 and grand_total > 0 else "FAIL"

        header = f"{'Category':<20} | {'Total':>5} | {'Passed':>6} | {'Failed':>6} | {'Pass %':>6}"
        separator = "-" * len(header)
        
        print("\n" + "="*55)
        print("--- Test Execution Summary ---".center(55))
        print(separator)
        print(header)
        print(separator)
        
        for cat, data in summary.items():
            pass_percent = f"{data['PASS']/data['Total'] * 100:.0f}%" if data['Total'] > 0 else "N/A"
            print(f"{cat:<20} | {data['Total']:>5} | {data['PASS']:>6} | {data['FAIL']:>6} | {pass_percent:>6}")

        print(separator)
        if grand_total > 0:
            print(f"{'TOTAL SUMMARY':<20} | {grand_total:>5} | {grand_pass:>6} | {grand_fail:>6} | {grand_pass/grand_total * 100:.0f}%")
        print("="*55)
        print(f"Overall Prompts tested: **{grand_total}**")
        print(f"Detailed report saved to: {self.output_json_path}\n")

        self._print_tool_summary()


    def evaluate(self) -> None:
        """
        Main function to read input, call Gemini (mocked), run evaluation logic, 
        and save the final results report, overwriting the previous one.
        """
        print(f"--- Starting Gemini Prompt Evaluation ---")
        print(f"Input: {self.input_json_path} | Output: {self.output_json_path}")
        print(f"Fuzzy Match Threshold: {FUZZY_MATCH_THRESHOLD}% | Overall Match Ratio: {MIN_KEYWORD_MATCH_RATIO:.0%}")
        
        try:
            data = self._load_json()
        except Exception:
            return 

        print(f"Processing {len(data)} prompts...")
        for item in data:
            result = self._run_single_test(item)
            self.all_results.append(result)

        # Save output JSON report (overwriting existing file)
        try:
            with open(self.output_json_path, "w") as file:
                json.dump([r.to_dict() for r in self.all_results], file, indent=4)
        except IOError:
            print(f"\n ERROR: Could not write output to: {self.output_json_path}")
            return

        self._print_summary_table()


if __name__ == "__main__":
    INPUT_FILE = "regression/tests/prompts.json" 
    OUTPUT_FILE = "regression/reports/output.json"

    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(reports_dir, exist_ok=True)

    FULL_OUTPUT_PATH = os.path.join(reports_dir, "output.json")

    if not os.path.exists(INPUT_FILE):
        print(f"\n ERROR: Corrected path check failed. File not found: {INPUT_FILE}")
        print("Ensure the file structure is correct (e.g., regression/tests/prompts.json exists).")
    else:
        evaluator = GeminiPromptEvaluator(INPUT_FILE, OUTPUT_FILE)
        evaluator.evaluate()