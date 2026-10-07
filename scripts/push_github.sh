#!/usr/bin/env bash
# 把本地已就绪的仓库推到 GitHub。
#
# 前置：先在 GitHub 网页上建一个**空**仓库（不要勾 README / .gitignore / license）。
# 用法：
#   bash scripts/push_github.sh git@github.com:<用户名>/<仓库名>.git
#   bash scripts/push_github.sh https://github.com/<用户名>/<仓库名>.git
#
# 脚本只做 push，不会改写任何提交历史。
set -euo pipefail

REPO_URL="${1:-}"
if [ -z "$REPO_URL" ]; then
  echo "用法: bash scripts/push_github.sh <空仓库地址>"
  echo "示例: bash scripts/push_github.sh git@github.com:yourname/recruit-csv-tool.git"
  exit 1
fi

cd "$(dirname "$0")/.."

# 幂等：重复执行不会因为 remote 已存在而失败
git remote remove origin 2>/dev/null || true
git remote add origin "$REPO_URL"

echo "==> 推送 main"
git push -u origin main

BRANCHES=(feature/1-overview feature/2-validate feature/3-stats feature/4-cli-ux)
for b in "${BRANCHES[@]}"; do
  echo "==> 推送 $b"
  git push origin "$b"
done

# 从仓库地址里抠出 owner/repo，用来拼 PR 链接
REMOTE_PATH="$(echo "$REPO_URL" | sed -E 's#^git@github.com:##; s#^https://github.com/##; s#\.git$##')"

cat <<EOF

推送完成。接下来开 4 个 PR，任选一种方式：

【方式 A】浏览器直接开（不用装任何东西），依次打开：
EOF
for b in "${BRANCHES[@]}"; do
  echo "  https://github.com/${REMOTE_PATH}/compare/main...${b}?expand=1"
done
cat <<EOF

【方式 B】装了 gh CLI 的话，一条命令：
  gh pr create --base main --head feature/1-overview --title "需求1：读入与概览" --body "见 README 需求 1 一节"
  gh pr create --base main --head feature/2-validate --title "需求2：校验与清洗" --body "见 README 需求 2 一节"
  gh pr create --base main --head feature/3-stats    --title "需求3：统计与导出" --body "见 README 需求 3 一节"
  gh pr create --base main --head feature/4-cli-ux   --title "命令行报错友好化" --body "见 README 错误提示一节"
EOF
