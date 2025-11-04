#!/usr/bin/env python3
"""测试Git提交API的正确格式"""

import json

# 测试数据
repo_id = "342513"
repo_full_name = "XCDMX/web-srd"
branch_name = "master"
file_path = "README.md"
file_content = "# Test\n\nHello"
commit_message = "测试提交"

print("=" * 60)
print("方式1: 直接传递字符串（不带外层引号）")
print("=" * 60)
data1 = {
    "operationType": "4",
    "repository": json.dumps({"repoId": repo_id, "repoFullName": repo_full_name}),
    "branch": json.dumps({"branchName": branch_name, "needReview": 0}),
    "files": json.dumps([{"fileType": 0, "filePath": file_path, "fileContent": file_content, "fileCommitMessage": commit_message}])
}
print("operationType:", repr(data1["operationType"]))
print("repository:", repr(data1["repository"]))
print()

print("=" * 60)
print("方式2: 值用双引号包裹（模拟curl --form格式）")
print("=" * 60)
repository_json = json.dumps({"repoId": repo_id, "repoFullName": repo_full_name})
branch_json = json.dumps({"branchName": branch_name, "needReview": 0})
files_json = json.dumps([{"fileType": 0, "filePath": file_path, "fileContent": file_content, "fileCommitMessage": commit_message}])

data2 = {
    "operationType": '"4"',
    "repository": f'"{repository_json}"',
    "branch": f'"{branch_json}"',
    "files": f'"{files_json}"'
}
print("operationType:", repr(data2["operationType"]))
print("repository:", repr(data2["repository"]))
print()

print("=" * 60)
print("根据你的curl命令分析")
print("=" * 60)
print("curl --form 'operationType=\"4\"' 实际上是：")
print("  字段名: operationType")
print("  字段值: \"4\" (包含双引号的字符串)")
print()
print("但这很不寻常，通常应该是：")
print("  字段值: 4 (不带引号)")
print()
print("建议: 先尝试方式1，如果不行再用方式2")
