from flask import Flask, render_template, request, jsonify
import pickle
import numpy as np
import pandas as pd
import random
from datetime import datetime, timedelta, date

app = Flask(__name__)

# 데이터 불러오기 및 전처리
data_orig = pd.read_csv("data/filtered_data.csv", encoding="utf-8")
data2 = pd.read_csv("data/통합시계열.csv", encoding="utf-8")
data = data_orig.copy()

# 소재지 column 생성
data["소재지"] = data["상세주소"] + " (" + data["건물명"] + ")"
data2["소재지"] = data2["주소"] + " (" + data2["건물명"] + ")"
data2["소재지"] = data2["소재지"].str.split(" ", n=1, expand=True)[1]

# 지역구별 데이터 갯수와 깡통전세 여부 확인
total_data_count = data.groupby("구").size()
filtered_data = data[data["전세가율"] >= 70]
filtered_data_count = filtered_data.groupby("구").size()

# 두 데이터를 딕셔너리로 묶기
summary = pd.DataFrame(
    {"Total": total_data_count, "Filtered": filtered_data_count}
).fillna(0)

# int로 변환
summary = summary.astype(int)

# 비율 계산
summary["Ratio"] = (summary["Filtered"] / summary["Total"]) * 100
# 한자리 수에서 반올림
summary["Ratio"] = summary["Ratio"].round(1)

# total 기준으로 내림차 정렬
summary = summary.sort_values(by="Total", ascending=False)


summary = summary.to_dict(orient="index")
summary = [
    {
        "Region": region,
        "Total": counts["Total"],
        "Filtered": counts["Filtered"],
        "Ratio": counts["Ratio"],
    }
    for region, counts in summary.items()
]

# get_data를 위한 데이터 변형
grouped = data.copy().dropna(subset=["전세가율"])
grouped = (
    grouped.groupby("소재지")
    .agg(
        {
            "구": "first",
            "월별평균 매매가": ["min", "max"],
            "월별평균 전세가": ["min", "max"],
            "전세가율": ["mean"],
        }
    )
    .reset_index()
)

grouped.columns = ["소재지", "구", "최소 매매가", "최대 매매가", "최소 전세가", "최대 전세가", "전세가율"]
grouped = grouped.astype(
    {"최소 매매가": "int", "최대 매매가": "int", "최소 전세가": "int", "최대 전세가": "int", "전세가율": "int"}
)
grouped.sort_values(by="전세가율", ascending=False, inplace=True)


@app.route("/")
def index():
    return render_template("index.html", summary=summary)


@app.route("/get_data", methods=["GET"])
def get_data():
    region = request.args.get("region")
    region_data = grouped[grouped["구"] == region]

    return jsonify(region_data.to_dict(orient="records")), 200


@app.route("/get_detail", methods=["GET"])
def get_detail():
    detail = request.args.get("detail")
    detail = detail

    detail_data = data2[data2["소재지"] == detail]
    detail_data["계약월"] = detail_data["계약월"].astype(str)

    jeonse_ratio = detail_data[detail_data["계약월"].str.startswith("2022")][
        ["월별평균 매매가", "월별평균 전세가"]
    ].mean()
    jeonse_ratio = jeonse_ratio[1] / jeonse_ratio[0] * 100

    detail_data = (
        detail_data.groupby("계약월")
        .agg(
            {
                "소재지": "first",
                "면적": "first",
                "월별평균 매매가": "mean",
                "월별평균 전세가": "mean",
                "건물용도": "first",
                "주소": "first",
                "건축년도": "first",
            }
        )
        .reset_index()
    )
    detail_data.columns = [
        "계약월",
        "소재지",
        "면적",
        "매매가",
        "전세가",
        "건물용도",
        "주소",
        "건축년도",
    ]

    detail_data[["평균 매매가", "평균 전세가"]] = detail_data[["매매가", "전세가"]].mean().astype(int)
    detail_data["전세가율"] = jeonse_ratio.round(2)

    return jsonify(detail_data.to_dict(orient="records")), 200


if __name__ == "__main__":
    # app.run(debug=True)
    app.run(host="0.0.0.0")
