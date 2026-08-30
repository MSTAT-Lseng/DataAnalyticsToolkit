"""文本与表格聚类功能测试。"""

import io
import json
import os
import tempfile
import unittest

import pandas as pd

from app import create_app
from utils.clustering import (
    clustering_column_details,
    cluster_documents,
    split_sentences,
)


class ClusteringBusinessTests(unittest.TestCase):
    def test_text_is_split_into_sentences(self):
        text = "苹果手机续航很好。物流服务很快！客服响应及时\n价格也很合理。"
        self.assertEqual(
            split_sentences(text),
            ["苹果手机续航很好。", "物流服务很快！", "客服响应及时", "价格也很合理。"],
        )

    def test_tfidf_kmeans_returns_clusters_keywords_and_projection(self):
        documents = [
            "苹果手机续航很好 屏幕清晰",
            "安卓手机运行流畅 屏幕清晰",
            "手机电池容量很大 续航持久",
            "物流速度很快 配送及时",
            "客服响应及时 服务态度很好",
            "快递配送速度很快 包装完整",
        ]
        result = cluster_documents(documents, 2)

        self.assertEqual(result["method"], "TF-IDF + K-Means")
        self.assertEqual(result["document_count"], 6)
        self.assertEqual(result["n_clusters"], 2)
        self.assertGreater(result["feature_count"], 0)
        self.assertEqual(len(result["clusters"]), 2)
        self.assertEqual(sum(item["size"] for item in result["clusters"]), 6)
        self.assertEqual(len(result["items"]), 6)
        self.assertTrue(all(1 <= item["cluster"] <= 2 for item in result["items"]))
        self.assertTrue(all("x" in item and "y" in item for item in result["items"]))
        self.assertTrue(any(cluster["keywords"] for cluster in result["clusters"]))

    def test_table_column_details_allow_text_columns(self):
        dataframe = pd.DataFrame({"内容": ["第一条", "第二条"], "空列": [None, ""]})
        details = clustering_column_details(dataframe)
        self.assertEqual(details[0]["name"], "内容")
        self.assertTrue(details[0]["eligible"])
        self.assertFalse(details[1]["eligible"])

    def test_invalid_text_and_cluster_count_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "至少需要 2"):
            cluster_documents(["只有一条"], 2)
        with self.assertRaisesRegex(ValueError, "没有可提取"):
            cluster_documents(["!!!", "???"], 2)
        with self.assertRaisesRegex(ValueError, "不能超过"):
            cluster_documents(["第一条", "第二条"], 3)


class ClusteringApiTests(unittest.TestCase):
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
            "编号,内容,备注\n"
            "1,苹果手机续航很好,甲\n"
            "2,安卓手机运行流畅,乙\n"
            "3,物流配送速度很快,丙\n"
            "4,客服响应及时,丁\n"
            "5,包装完整配送及时,戊\n"
            "6,手机电池容量很大,己\n"
        ).encode()

    def test_text_clustering_endpoint(self):
        response = self.client.post(
            "/api/heat-analysis/clustering",
            data={
                "mode": "text",
                "text": "苹果手机续航很好。安卓手机运行流畅。物流配送速度很快。客服响应及时。",
                "n_clusters": "2",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        result = response.get_json()["result"]
        self.assertEqual(result["source_mode"], "text")
        self.assertEqual(result["document_count"], 4)
        self.assertEqual(result["n_clusters"], 2)

    def test_table_preview_and_clustering_endpoint(self):
        response = self.client.post(
            "/api/heat-analysis/clustering/preview",
            data={"file": (io.BytesIO(self.csv_bytes()), "reviews.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        preview = response.get_json()
        self.assertEqual(preview["columns"], ["编号", "内容", "备注"])
        self.assertTrue(preview["column_details"][1]["eligible"])

        response = self.client.post(
            "/api/heat-analysis/clustering",
            data={
                "mode": "table",
                "file": (io.BytesIO(self.csv_bytes()), "reviews.csv"),
                "column": "内容",
                "n_clusters": json.dumps(2),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        result = response.get_json()["result"]
        self.assertEqual(result["source_mode"], "table")
        self.assertEqual(result["source_column"], "内容")
        self.assertEqual(result["document_count"], 6)
        self.assertEqual([item["index"] for item in result["items"]], [2, 3, 4, 5, 6, 7])

    def test_clustering_requires_a_valid_mode_and_two_sentences(self):
        response = self.client.post(
            "/api/heat-analysis/clustering",
            data={"mode": "text", "text": "只有一句话", "n_clusters": "2"},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("至少需要 2 个句子", response.get_json()["error"])

        response = self.client.post(
            "/api/heat-analysis/clustering",
            data={"mode": "other", "n_clusters": "2"},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("不支持", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
