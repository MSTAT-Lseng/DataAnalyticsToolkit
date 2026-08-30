"""回归分析功能测试。"""

import io
import json
import os
import tempfile
import unittest

import openpyxl
import pandas as pd

from app import create_app
from utils.regression import pairwise_regression, regression_column_details


class RegressionBusinessTests(unittest.TestCase):
    def setUp(self):
        self.dataframe = pd.DataFrame({
            "服务": [1, 2.5, 5, 10],
            "质量": [2, 3.5, 7, 9.5],
            "价格": [10, 8.5, 4, 1],
            "备注": ["A", "B", "C", "D"],
        })

    def test_only_complete_1_to_10_numeric_columns_are_eligible(self):
        details = regression_column_details(self.dataframe)
        eligible = [item["name"] for item in details if item["eligible"]]
        self.assertEqual(eligible, ["服务", "质量", "价格"])
        self.assertEqual(details[-1]["reason"], "包含空值或非数字")

    def test_pairwise_results_follow_selected_column_order(self):
        results = pairwise_regression(self.dataframe, ["服务", "质量", "价格"])
        self.assertEqual(
            [(item["x_label"], item["y_label"]) for item in results],
            [("服务", "质量"), ("服务", "价格"), ("质量", "价格")],
        )
        self.assertTrue(all(item["sample_count"] == 4 for item in results))

    def test_out_of_range_column_is_rejected(self):
        dataframe = pd.DataFrame({"A": [1, 11], "B": [2, 3]})
        self.assertFalse(regression_column_details(dataframe)[0]["eligible"])
        with self.assertRaisesRegex(ValueError, "1-10"):
            pairwise_regression(dataframe, ["A", "B"])


class RegressionApiTests(unittest.TestCase):
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
        return "服务,质量,价格,备注\n1,2,10,A\n2.5,3.5,8.5,B\n5,7,4,C\n10,9.5,1,D\n".encode()

    @staticmethod
    def xlsx_bytes():
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["服务", "质量", "非数值"])
        sheet.append([1, 2, "A"])
        sheet.append([2.5, 3.5, "B"])
        sheet.append([5, 7, "C"])
        sheet.append([10, 9.5, "D"])
        output = io.BytesIO()
        workbook.save(output)
        return output.getvalue()

    def test_csv_preview_and_multi_pair_analysis(self):
        response = self.client.post(
            "/api/regression/preview",
            data={"file": (io.BytesIO(self.csv_bytes()), "ratings.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        preview = response.get_json()
        self.assertEqual(preview["eligible_columns"], ["服务", "质量", "价格"])
        self.assertEqual(preview["columns"], ["服务", "质量", "价格", "备注"])

        response = self.client.post(
            "/api/regression",
            data={
                "file": (io.BytesIO(self.csv_bytes()), "ratings.csv"),
                "columns": json.dumps(["服务", "质量", "价格"]),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["result"]["pair_count"], 3)

    def test_xlsx_preview_and_manual_endpoint_removed(self):
        response = self.client.post(
            "/api/regression/preview",
            data={"file": (io.BytesIO(self.xlsx_bytes()), "ratings.xlsx")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["eligible_columns"], ["服务", "质量"])

        response = self.client.post(
            "/api/regression/manual",
            json={"data": [{"x": 1, "y": 2}, {"x": 2, "y": 3}]},
        )
        self.assertEqual(response.status_code, 404)

    def test_analysis_requires_two_columns(self):
        response = self.client.post(
            "/api/regression",
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
