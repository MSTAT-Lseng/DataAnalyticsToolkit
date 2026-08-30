"""热力分析功能测试。"""

import io
import json
import os
import tempfile
import unittest

import openpyxl
import pandas as pd

from app import create_app
from utils.heat_analysis import heatmap_values
from utils.regression import regression_column_details


class HeatAnalysisBusinessTests(unittest.TestCase):
    def setUp(self):
        self.dataframe = pd.DataFrame({
            "服务": [1, 2, 5, 10],
            "质量": [2, 4, 6, 8],
            "价格": [10, 8, 5, 1],
            "备注": ["A", "B", "C", "D"],
        })

    def test_eligible_columns_match_numeric_1_to_10_rule(self):
        details = regression_column_details(self.dataframe)
        eligible = [item["name"] for item in details if item["eligible"]]
        self.assertEqual(eligible, ["服务", "质量", "价格"])

    def test_heatmap_contains_symmetric_pearson_matrix(self):
        result = heatmap_values(self.dataframe, ["服务", "质量", "价格"])

        self.assertEqual(result["columns"], ["服务", "质量", "价格"])
        self.assertEqual(len(result["values"]), 3)
        self.assertTrue(all(len(row) == 3 for row in result["values"]))
        self.assertTrue(all(result["values"][i][i] == 1 for i in range(3)))
        self.assertAlmostEqual(result["values"][0][1], 0.958315, places=5)
        self.assertAlmostEqual(result["values"][0][2], -0.989967, places=5)
        self.assertEqual(result["values"][1][0], result["values"][0][1])

    def test_out_of_range_column_is_rejected(self):
        dataframe = pd.DataFrame({"A": [1, 11], "B": [2, 3]})
        with self.assertRaisesRegex(ValueError, "1-10"):
            heatmap_values(dataframe, ["A", "B"])

    def test_constant_column_uses_zero_for_undefined_cross_value(self):
        dataframe = pd.DataFrame({"A": [5, 5, 5], "B": [1, 2, 3]})
        result = heatmap_values(dataframe, ["A", "B"])
        self.assertEqual(result["values"], [[1.0, 0.0], [0.0, 1.0]])


class HeatAnalysisApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        class TestConfig:
            TESTING = True
            SECRET_KEY = "test"
            UPLOAD_FOLDER = self.temp_dir.name
            LOG_FILE = os.path.join(self.temp_dir.name, "app.log")
            MPL_BACKEND = "Agg"

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def csv_bytes():
        return (
            "服务,质量,价格,备注\n"
            "1,2,10,A\n"
            "2,4,8,B\n"
            "5,6,5,C\n"
            "10,8,1,D\n"
        ).encode()

    @staticmethod
    def xlsx_bytes():
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["服务", "质量", "文本"])
        sheet.append([1, 2, "A"])
        sheet.append([2, 4, "B"])
        sheet.append([5, 6, "C"])
        sheet.append([10, 8, "D"])
        output = io.BytesIO()
        workbook.save(output)
        return output.getvalue()

    def test_csv_preview_and_heat_analysis(self):
        response = self.client.post(
            "/api/heat-analysis/preview",
            data={"file": (io.BytesIO(self.csv_bytes()), "ratings.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        preview = response.get_json()
        self.assertEqual(preview["eligible_columns"], ["服务", "质量", "价格"])
        self.assertEqual(preview["columns"], ["服务", "质量", "价格", "备注"])

        response = self.client.post(
            "/api/heat-analysis",
            data={
                "file": (io.BytesIO(self.csv_bytes()), "ratings.csv"),
                "columns": json.dumps(["服务", "质量", "价格"]),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        result = response.get_json()["result"]
        self.assertEqual(result["columns"], ["服务", "质量", "价格"])
        self.assertEqual(result["sample_count"], 4)
        self.assertEqual(len(result["values"]), 3)

    def test_xlsx_preview_and_separate_public_entries(self):
        response = self.client.post(
            "/api/heat-analysis/preview",
            data={"file": (io.BytesIO(self.xlsx_bytes()), "ratings.xlsx")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["eligible_columns"], ["服务", "质量"])

        response = self.client.get("/heat-analysis")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("热力分析", page)
        self.assertIn("/static/js/heat_analysis.js", page)
        self.assertNotIn("cluster-text-form", page)
        self.assertNotIn("/static/js/clustering.js", page)

        response = self.client.get("/clustering")
        self.assertEqual(response.status_code, 200)
        clustering_page = response.get_data(as_text=True)
        self.assertIn("聚类分析", clustering_page)
        self.assertIn("cluster-text-form", clustering_page)
        self.assertIn("/static/js/clustering.js", clustering_page)
        self.assertIn('class="tool-nav-item tool-nav-subitem active"', clustering_page)
        self.assertNotIn("维度挖掘", page)
        self.assertEqual(self.client.get("/dimension-mining").status_code, 404)

    def test_analysis_requires_two_columns(self):
        response = self.client.post(
            "/api/heat-analysis",
            data={
                "file": (io.BytesIO(self.csv_bytes()), "ratings.csv"),
                "columns": json.dumps(["服务"]),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("至少选择 2 列", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
