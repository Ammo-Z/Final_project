#!/bin/bash
# ============================================================
# ECO-Impact Interpreter — GitHub Setup Script
# ============================================================
# 使用方法:
#   1. 先在 GitHub 网站上创建空仓库 (不要勾选 Add README)
#   2. 把下面的 YOUR_GITHUB_USERNAME 改成你的 GitHub 用户名
#   3. 打开终端，运行: bash setup_github.sh
# ============================================================

# ⚠️ 修改这里为你的 GitHub 用户名
GITHUB_USER="YOUR_GITHUB_USERNAME"
REPO_NAME="eco-impact-interpreter"

echo "============================================"
echo "  ECO-Impact Interpreter — GitHub Setup"
echo "============================================"

# Step 1: 初始化 Git
echo ""
echo "[Step 1/4] Initializing Git repository..."
git init
echo "✅ Git initialized"

# Step 2: 添加所有文件
echo ""
echo "[Step 2/4] Adding all files..."
git add .
echo "✅ Files staged"

# Step 3: 创建初始提交
echo ""
echo "[Step 3/4] Creating initial commit..."
git commit -m "Initial commit: ECO-Impact Interpreter v1.0

- 5-stage agentic pipeline (Parse → RAG → Draft → Critique → Finalize)
- Triple-index RAG knowledge base (800 glossary + 120 ECO cases + 20 MSA sections)
- 30-case synthetic evaluation set with Gold Standard briefs
- Streamlit Decision Cockpit with Demo mode
- Model-as-a-Judge evaluation framework with Cohen's kappa
- Chain-of-Thought drafting + Self-Reflexion critique agents

BU.330.760.T1 Generative AI | Johns Hopkins Carey Business School"
echo "✅ Initial commit created"

# Step 4: 推送到 GitHub
echo ""
echo "[Step 4/4] Pushing to GitHub..."
git branch -M main
git remote add origin "https://github.com/${GITHUB_USER}/${REPO_NAME}.git"
git push -u origin main
echo "✅ Pushed to GitHub"

echo ""
echo "============================================"
echo "  🎉 Done! Your repo is live at:"
echo "  https://github.com/${GITHUB_USER}/${REPO_NAME}"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. cp .env.example .env && nano .env   # 填入 API Key"
echo "  2. pip install -r requirements.txt"
echo "  3. python scripts/build_index.py        # 构建 RAG 索引"
echo "  4. streamlit run src/ui/app.py           # 启动应用"
