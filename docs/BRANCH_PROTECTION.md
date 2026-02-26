# Branch Protection Rules Setup

## Overview

This document outlines the mandatory branch protection rules that must be configured in GitHub to ensure code quality and safety before merging to main branches.

## 🚨 Required Branch Protection

### Main Branch Protection

**Repository Settings → Branches → Branch protection rule**

**Branch name pattern:** `main`

**Required Status Checks:**
- [x] `Require status checks to pass before merging`
- [x] `Require branches to be up to date before merging`

**Required checks:**
- [x] `game-tests / test` (CI workflow)
- [x] `game-tests / security` (Security scan)
- [x] `game-tests / performance` (Performance tests - main only)

**Additional protections:**
- [x] `Require pull request reviews before merging`
- [x] `Dismiss stale PR approvals when new commits are pushed`
- [x] `Require review from CODEOWNERS`
- [x] `Require approval for PR edits by maintainers`
- [x] `Limit who can dismiss pull request reviews` (Maintainers only)
- [x] `Restrict pushes that create files` (Maintainers only)
- [x] `Do not allow bypassing the above settings`

### Dev Branch Protection

**Branch name pattern:** `dev`

**Required Status Checks:**
- [x] `Require status checks to pass before merging`
- [x] `Require branches to be up to date before merging`

**Required checks:**
- [x] `game-tests / test` (CI workflow)
- [x] `game-tests / security` (Security scan)

**Additional protections:**
- [x] `Require pull request reviews before merging`
- [x] `Dismiss stale PR approvals when new commits are pushed`

## 📋 Setup Instructions

### 1. Navigate to Branch Protection

1. Go to your GitHub repository
2. Click **Settings** tab
3. Click **Branches** in left sidebar
4. Click **Add branch protection rule**

### 2. Configure Main Branch

**Branch name pattern:**
```
main
```

**Status checks:**
- ✅ Require status checks to pass before merging
- ✅ Require branches to be up to date before merging

**Required status checks:**
- ✅ `game-tests / test`
- ✅ `game-tests / security` 
- ✅ `game-tests / performance`

**Pull request requirements:**
- ✅ Require pull request reviews before merging
- ✅ Dismiss stale PR approvals when new commits are pushed
- ✅ Require review from CODEOWNERS
- ✅ Require approval for PR edits by maintainers
- ✅ Limit who can dismiss pull request reviews (Maintainers only)

**Additional restrictions:**
- ✅ Restrict pushes that create files (Maintainers only)
- ✅ Do not allow bypassing the above settings

### 3. Configure Dev Branch

**Branch name pattern:**
```
dev
```

**Status checks:**
- ✅ Require status checks to pass before merging
- ✅ Require branches to be up to date before merging

**Required status checks:**
- ✅ `game-tests / test`
- ✅ `game-tests / security`

**Pull request requirements:**
- ✅ Require pull request reviews before merging
- ✅ Dismiss stale PR approvals when new commits are pushed

### 4. Create CODEOWNERS File

Create `.github/CODEOWNERS`:

```
# CODEOWNERS File

# Global owners for all files
* @maintainer-team @lead-developer

# Specific file owners
.github/workflows/* @devops-team
tests/* @qa-team
services/* @backend-team
models/* @backend-team
cogs/* @discord-team
```

## 🔒 What This Guarantees

### Every Code Change Must Prove:

✅ **Smoke Tests Pass**
- Black Pack guarantee
- Legendary caps enforcement
- No duplicate cards
- Trade atomicity
- Refund revocation
- Rate limiting

✅ **Security Checks Pass**
- No hardcoded secrets
- No obvious vulnerabilities
- Code quality standards

✅ **Performance Standards (Main Branch)**
- Rate limiter performance
- Database query efficiency
- Memory usage limits

✅ **Code Review**
- At least one maintainer approval
- CODEOWNERS review required
- Stale approvals dismissed on new commits

✅ **Up-to-Date Branches**
- No merge conflicts
- Latest main/dev code included
- All tests run on current code

## 🚀 Merge Requirements

### To Merge to `main`:

1. **All Tests Pass:**
   - Smoke tests ✅
   - Security scan ✅
   - Performance tests ✅

2. **Code Review:**
   - Maintainer approval ✅
   - CODEOWNERS approval ✅
   - No stale approvals ✅

3. **Branch Status:**
   - Up to date with main ✅
   - No merge conflicts ✅

### To Merge to `dev`:

1. **All Tests Pass:**
   - Smoke tests ✅
   - Security scan ✅

2. **Code Review:**
   - Maintainer approval ✅
   - No stale approvals ✅

3. **Branch Status:**
   - Up to date with dev ✅
   - No merge conflicts ✅

## 📊 CI Pipeline Flow

```
Developer Push → PR Created → CI Runs → Tests Pass → Review → Merge
     ↓                ↓           ↓          ↓        ↓        ↓
  Feature Branch   Pull Request  All Jobs   Green    Approved  Deploy
```

### CI Jobs Breakdown:

1. **test** - Main smoke test suite
   - Black Pack guarantee
   - Legendary caps
   - Parallel safety
   - Trade atomicity
   - Rate limiting
   - Refund revocation

2. **security** - Security scanning
   - Secret detection
   - Basic vulnerability scan
   - Code quality checks

3. **performance** - Performance validation (main only)
   - Rate limiter benchmarks
   - Database performance
   - Memory usage checks

## 🛠️ Troubleshooting

### Common Issues:

**"Required status check missing"**
- Check that CI workflow names match exactly
- Verify workflow is running on PR
- Check GitHub Actions permissions

**"CODEOWNERS approval required"**
- Verify CODEOWNERS file exists
- Check team member permissions
- Ensure CODEOWNERS are in the repository

**"Branch not up to date"**
- Sync with target branch
- Resolve merge conflicts
- Re-run CI if needed

**"Tests failing"**
- Check smoke test output
- Fix failing business logic
- Verify test environment setup

### Emergency Bypass:

In emergency situations, maintainers can:

1. Temporarily disable specific rules
2. Use admin override (if configured)
3. Merge directly to main (bypassing protection)

**⚠️ Use emergency bypass only for critical fixes!**

## 📋 Pre-Merge Checklist

Before creating a PR:

- [ ] Code passes local smoke tests
- [ ] No hardcoded secrets added
- [ ] Performance impact considered
- [ ] Documentation updated if needed
- [ ] Tests cover new functionality

Before merging:

- [ ] All CI checks pass ✅
- [ ] Code review approved ✅
- [ ] Branch up to date ✅
- [ ] No merge conflicts ✅
- [ ] Emergency bypass not needed ✅

## 🎯 Benefits

### Code Quality:
- Every change tested automatically
- Security vulnerabilities caught early
- Performance regressions prevented
- Code review enforced

### Safety:
- No broken code reaches main
- Emergency procedures documented
- Rollback capabilities maintained
- Audit trail preserved

### Team Workflow:
- Clear merge requirements
- Automated quality gates
- Consistent review process
- Reduced manual overhead

---

**🚀 With these protections in place, every merge to main guarantees production-ready code!**
