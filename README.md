<div align="center">
  <img src="code-companion/public/logo.svg" alt="Ling Guang Logo" width="128" height="128">
  <h1>灵光 (Ling Guang)</h1>
</div>

<div align="center">
  <p>
    <a href="README_en.md">English</a> | <b>中文</b>
  </p>
</div>

一个适配移动端的网页客户端，用于与多种 AI CLi（包括 Claude code、Codex 和 Gemini cli）进行交互。它提供了一个聊天界面，用于管理不同的聊天会话、项目，并查看使用情况统计。

## 主要功能

- **多模型支持**: 在 Claude、Codex、Gemini 等多种 AI 模型之间无缝切换。
- **移动端优先设计**: 完全响应式的界面，在桌面和移动设备上均有良好体验。
- **实时聊天**: 支持 Markdown 渲染和代码语法高亮的交互式聊天界面。
- **会话与项目管理**: 按会话组织您的聊天，并将它们链接到不同的项目。
- **使用情况统计**: 监控令牌（Token）使用情况，并检查 AI 引擎的实时状态。
- **插件系统**: 通过自定义插件扩展核心功能。
- **提示词管理**: 创建、编辑和管理系统提示词，以定制 AI 的行为。
## 目录

- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [系统架构](#系统架构)
- [项目截图](#项目截图)
- [快速开始](#快速开始)
- [文档与说明](#文档与说明)
- [许可证](#许可证)

## 项目简介

灵光是为 AI 驱动的代码开发流程量身打造的 Web 平台，支持多引擎统一接入与切换。它面向个人与团队提供可控、可追踪、可扩展的 AI 辅助开发体验，并兼顾移动端访问。未来将提供飞书机器人对话入口。

## 核心特性

- 多引擎支持：Claude、Codex、Gemini 统一管理与切换
- 项目管理：项目/会话组织与检索
- 会话控制：上下文管理、权限与指令控制
- 成本追踪：用量统计与成本分析
- 智能翻译：中英互译与术语一致性维护
- 扩展能力：插件/技能体系
- 多端可用：桌面与移动端友好
- 机器人接入：飞书机器人对话（规划中）

## 系统架构

灵光采用前后端分离与多引擎编排的架构，核心组件如下：

- 前端 Web：提供可视化操作与多端适配界面
- 后端服务：统一 API、会话与项目管理、成本统计、翻译与插件系统
- 引擎适配层：对接 Claude、Codex、Gemini 等 CLI/SDK
- 扩展机制：技能/插件注册、配置与权限控制

数据流概览：

1. 用户在前端创建项目/会话
2. 后端汇总上下文与配置，路由至指定引擎
3. 引擎返回结果并写入会话记录与统计
4. 前端展示结果并支持继续迭代

## 项目截图

<img src="img.png" width="640" alt="Lingguang Screenshot" />

## 快速开始

请先阅读子项目文档：

- 前端：[code-companion/README.md](code-companion/README.md)
- 后端：[backend/README.md](backend/README.md)

## 文档与说明

- 前端文档：[code-companion/README.md](code-companion/README.md)（支持按需调整与二次开发）
- 后端文档：[backend/README.md](backend/README.md)（支持按需调整与二次开发）

## 许可证

本项目采用 MIT License，详见 `LICENSE`。
