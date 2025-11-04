import requests

url = "https://www.srdcloud.cn/api/codebackend/codecenter/gitclient/v1/commitFiles"

# 使用 files 参数发送 multipart/form-data 格式
files = {
    'operationType': (None, '4'),
    'repository': (None, '{"repoId":"342513","repoFullName":"XCDMX/web-srd"}'),
    'branch': (None, '{"branchName":"master","needReview":0}'),
    'files': (None, '[{"fileType":0,"filePath":"README.md","fileContent":"# web-srd\\n\\n   HELLO1   ","fileCommitMessage":"更新文件 web-srd/README.md"}]')
}

headers = {
    'projectid': '25718',
    'sessionid': 'c699b466-3e35-4cc1-b3ec-3e064f66a8aa',
    'userid': '186812'
}

response = requests.post(url, headers=headers, files=files)

print(response.text)
