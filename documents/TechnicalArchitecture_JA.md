# 技術アーキテクチャ

[English](./TechnicalArchitecture.md) | **日本語**

このセクションでは、統合データ分析プラットフォームを支えるコンポーネントとインタラクションについて説明します。このアーキテクチャは、顧客情報、製品詳細、取引履歴を取り込み、インタラクティブな Web エクスペリエンスを通じてインサイトを提供します。

> **カスタマイズ情報**: 本リポジトリでの追加カスタマイズ（Agent Mode, APIM AI Gateway, MCP Server, Guardrails, GPT-5 等）の詳細は [Agent-Architecture.md](./Agent-Architecture.md), [Implementation-Overview.md](./Implementation-Overview.md), [アーキテクチャ図](../ARCHITECTURE.md) を参照してください。

#### オプション 1: Microsoft Fabric と Microsoft Copilot Studio を使用したアーキテクチャ

![image](./Images/ReadMe/solution-architecture-cps.png)

### 顧客 / 製品 / 取引詳細
顧客、製品、取引詳細の SQL スクリプトがシステムへの主要な入力です。これらのテーブルはアップロードされ、ダウンストリームでのインサイト生成のために保存されます。

### SQL Database in Fabric
アップロードされた顧客情報、製品詳細、取引履歴テーブルを保存します。Fabric Data Agent でインサイトを提供するための主要なナレッジソースとして機能します。

### Fabric Data Agent
自然言語クエリをサポートする大規模言語モデル（LLM）機能を提供します。

### Microsoft Copilot Studio
Fabric Data Agent は Microsoft Copilot Studio のエージェントに接続され、Microsoft Teams のチャネルとして公開されます。

### Microsoft Teams
ユーザーは Microsoft Teams 内で直接、データインサイトの探索、トレンドの可視化、自然言語での質問ができます。


#### オプション 2: Microsoft Fabric と Microsoft Foundry を使用したアーキテクチャ

![image](./Images/ReadMe/solution-architecture.png)

### 顧客 / 製品 / 取引詳細
顧客、製品、取引詳細の SQL スクリプトがシステムへの主要な入力です。これらのテーブルはアップロードされ、ダウンストリームでのインサイト生成のために保存されます。

### SQL Database in Fabric
アップロードされた顧客情報、製品詳細、取引履歴テーブルを保存します。Web アプリケーションでインサイトを提供するための主要なナレッジソースとして機能します。また、Web インターフェースのチャット履歴とセッションコンテキストを保持します。過去のインタラクションの取得を可能にします。

### Microsoft Foundry
自然言語クエリをサポートする大規模言語モデル（LLM）機能を提供します。

### Agent Framework
コンテキスト化された応答と、取得されたデータに対するマルチステップ推論のためのオーケストレーションとインテリジェントな関数/ツール呼び出しを処理します。

### App Service
AI サービスとストレージレイヤーとインターフェースする Web アプリケーションと API レイヤーをホストします。ユーザーセッションを管理し、REST コールを処理します。

### Container Registry
ホスティング環境で使用するコンテナ化されたデプロイメントを保存します。

### Web フロントエンド
ユーザーがデータインサイトを探索し、トレンドを可視化し、自然言語で質問し、チャートを生成できるインタラクティブな UI です。リアルタイムインタラクションのために SQL Database in Fabric と App Service に直接接続します。
