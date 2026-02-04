# 統合データ基盤のための Agentic アプリケーション

[English](README_EN.md) | **日本語**

> **🛠️ 本プロジェクトについて**  
> このリポジトリは [microsoft/agentic-applications-for-unified-data-foundation-solution-accelerator](https://github.com/microsoft/agentic-applications-for-unified-data-foundation-solution-accelerator) をベースに、Hackathon 向けにカスタマイズしたプロジェクトです。

<br/>

このソリューションアクセラレータは、Microsoft Fabric の統合データ基盤上に構築された Agentic AI ソリューションを活用し、組織が迅速かつスマートな意思決定を大規模に行えるよう支援します。Microsoft Foundry エージェントと Agent Framework オーケストレーションのシームレスな統合により、日常的なプロセスを自動化し、業務を効率化し、企業データセット全体に対する自然言語クエリを可能にするインテリジェントなワークフローを設計できます。これにより、ガバナンスされた高品質なデータが技術専門家だけでなくビジネスユーザーにもアクセス可能となり、インサイトが容易に得られ、信頼できる情報に基づいた意思決定が可能な共有環境を構築します。

<br/>

<div align="center">
  
[**ソリューション概要**](#ソリューション概要)  \| [**クイックデプロイ**](#クイックデプロイ)  \| [**ビジネスシナリオ**](#ビジネスシナリオ)  \| [**関連ドキュメント**](#関連ドキュメント)

</div>
<br/>

**注意:** これらのテンプレートを使用して作成する AI ソリューションについては、関連するすべてのリスクを評価し、適用されるすべての法律および安全基準を遵守する責任があります。詳細は [Agent Service](https://learn.microsoft.com/ja-jp/azure/ai-foundry/responsible-ai/agents/transparency-note) および [Agent Framework](https://github.com/microsoft/agent-framework/blob/main/TRANSPARENCY_FAQ.md) の透明性ドキュメントをご覧ください。
<br/>

<h2><img src="./documents/Images/ReadMe/solution-overview.png" width="48" />
ソリューション概要
</h2>

Fabric の統合データ基盤アクセラレータ、SQL Database in Fabric、Agent Framework、AI Foundry を活用して構造化データをクエリします。構造化データセットは、セマンティックモデルとデータアセットを探索するためのインタラクティブな Web フロントエンドを通じて、インテリジェントかつオーケストレーションされた応答によって分析されます。インサイトは自然言語を使用して生成されます。

### ソリューションアーキテクチャ

Microsoft Fabric と Microsoft Copilot Studio:

|![image](./documents/Images/ReadMe/solution-architecture-cps.png)
|---|

Microsoft Fabric と Microsoft Foundry:

|![image](./documents/Images/ReadMe/solution-architecture.png)
|---|

### 追加リソース

[技術アーキテクチャ](./documents/TechnicalArchitecture.md)

<br/>
<h2>

機能
</h2>

### 主な機能

<details open>  

<summary>このソリューションが実現する主要機能について詳しく見る</summary>  

**Microsoft Fabric + Microsoft Foundry 上に構築**

- **Fabric による統合データ基盤** <br/>  
Microsoft Fabric と統合データ基盤の基本機能を活用し、オーケストレーション、検索、ユーザーエクスペリエンスにおいて優れたインテリジェントエージェントを構築

- **スケーラブルなガバナンスされたデータ** <br/>  
Fabric のデータ基盤とシームレスに統合し、パフォーマンス、スケーラビリティ、拡張性を確保

- **自然言語インタラクション** <br/>  
Microsoft Foundry エージェントがオーケストレーションと検索を調整し、迅速でコンテキストに即した回答を提供してインサイトを加速。企業データアセット全体への統一アクセスを可能にする直感的な自然言語クエリ機能を実現

</details>

<br /><br />
<h2><img src="./documents/Images/ReadMe/quick-deploy.png" width="48" />

クイックデプロイ
</h2>

### インストール・デプロイ方法

このソリューションを自身の Azure サブスクリプションにデプロイするには、デプロイガイドのクイックデプロイ手順に従ってください。

Azure デプロイ: [デプロイガイドはこちら](./documents/DeploymentGuide.md)
<br/><br/>

- [ローカル開発セットアップガイド](./documents/LocalDevelopmentSetup.md) - Windows および Linux 向けの包括的なセットアップ手順
- ネイティブ Windows セットアップ、WSL2 構成、クロスプラットフォーム開発ツールを含む
<br/><br/>

| [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/naoki1213mj/hackathon202601-stu-se-agentic-ai) | [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/naoki1213mj/hackathon202601-stu-se-agentic-ai) |

|---|---|

<br/>

> ⚠️ **重要: Azure OpenAI クォータの確認**

 <br/>サブスクリプションで十分なクォータが利用可能であることを確認するため、ソリューションをデプロイする前に[クォータ確認手順ガイド](./documents/QuotaCheck.md)に従ってください。

<br/>

### 前提条件とコスト

このソリューションアクセラレータをデプロイするには、**リソースグループ、リソース、アプリ登録の作成、およびリソースグループレベルでのロール割り当て**に必要な権限を持つ [Azure サブスクリプション](https://azure.microsoft.com/ja-jp/free/)へのアクセスが必要です。これには、サブスクリプションレベルでの共同作成者ロールと、サブスクリプションおよび/またはリソースグループレベルでのロールベースアクセス制御ロールが含まれます。[Azure アカウントセットアップ](./documents/AzureAccountSetUp.md)の手順に従ってください。また、最低 F2 の Fabric 容量が必要です。[Fabric 容量セットアップ](https://learn.microsoft.com/ja-jp/fabric/admin/capacity-settings?tabs=fabric-capacity#create-a-new-capacity)の手順に従ってください。

サービスが利用可能なリージョンの例: East US、East US2、Australia East、UK South、France Central、Japan East

[リージョン別 Azure 製品](https://azure.microsoft.com/ja-jp/explore/global-infrastructure/products-by-region/?products=all&regions=all)ページで、以下のサービスが利用可能な**リージョン**を選択してください。

料金はリージョンと使用量によって異なるため、正確なコストを予測することはできません。このインフラストラクチャで使用される Azure リソースの大部分は使用量ベースの価格設定です。ただし、Azure Container Registry（レジストリごとの固定日額コスト）や、プロビジョニング時の Cosmos DB や SQL Database などの一部のサービスは、実際の使用量に関係なく基本料金が発生する場合があります。

[Azure 料金計算ツール](https://azure.microsoft.com/ja-jp/pricing/calculator)および [Fabric 容量見積もりツール](https://www.microsoft.com/ja-jp/microsoft-fabric/capacity-estimator)を使用して、サブスクリプションでのソリューションのコストを計算してください。

[サンプル料金シート](https://azure.com/e/708895d4fc4449b1826016fad8a83fe0)を参照して、使用量のカスタマイズとスケーリングにご活用ください。

_注: これはすべてのコストを網羅したものではありません。選択した SKU、スケールされた使用量、カスタマイズ、および独自のテナントへの統合により、このサンプルソリューションの総消費量に影響を与える可能性があります。サンプル料金シートは、特定のニーズに合わせて見積もりをカスタマイズするための出発点として提供されています。_

<br/>

| 製品 | 説明 | ティア / 想定使用量 | コスト |
|---|---|---|---|
| [Microsoft Foundry](https://learn.microsoft.com/ja-jp/azure/ai-foundry) | Azure AI サービスを組み合わせた AI ワークフローのオーケストレーションと構築に使用 | Free ティア | [料金](https://azure.microsoft.com/ja-jp/pricing/details/ai-studio/) |
| [Azure AI Services (OpenAI)](https://learn.microsoft.com/ja-jp/azure/cognitive-services/openai/overview) | GPT モデルを使用した言語理解とチャット機能を実現 | S0 ティア; トークン量と使用モデル（例: GPT-5, GPT-4o-mini）に応じた料金 | [料金](https://azure.microsoft.com/ja-jp/pricing/details/cognitive-services/) |
| [Azure App Service](https://learn.microsoft.com/ja-jp/azure/app-service/overview) | フロントエンドとバックエンド API サービスをホスト | B1/P1v2 ティア; プランごとの固定月額 | [料金](https://azure.microsoft.com/ja-jp/pricing/details/app-service/) |
| [Azure Container Registry](https://learn.microsoft.com/ja-jp/azure/container-registry/container-registry-intro) | Azure App Service で使用されるコンテナイメージを保存・提供 | Basic/Premium ティア; レジストリごとの固定日額 | [料金](https://azure.microsoft.com/ja-jp/pricing/details/container-registry/) |
| [Azure API Management](https://learn.microsoft.com/ja-jp/azure/api-management/api-management-key-concepts) | AI Gateway としてトークン計測、認証、回路遮断を提供 | Consumption ティア; 従量課金 | [料金](https://azure.microsoft.com/ja-jp/pricing/details/api-management/) |
| [Azure API Center](https://learn.microsoft.com/ja-jp/azure/api-center/overview) | MCP Server やAI API のツールカタログ・ガバナンス | Free ティア | [料金](https://azure.microsoft.com/ja-jp/pricing/details/api-center/) |
| [Azure Monitor / Log Analytics](https://learn.microsoft.com/ja-jp/azure/azure-monitor/logs/log-analytics-overview) | サービスとコンテナからのテレメトリとログを収集・分析 | 従量課金; データ取り込み量に応じた料金 | [料金](https://azure.microsoft.com/ja-jp/pricing/details/monitor/) |
| [SQL Database in Fabric](https://learn.microsoft.com/ja-jp/fabric/fundamentals/microsoft-fabric-overview) | インサイト、メタデータ、チャット履歴を含む構造化データを保存 | F2 容量; 容量ごとの固定月額 | [料金](https://azure.microsoft.com/ja-jp/pricing/details/microsoft-fabric/) |

<br/>

>⚠️ **重要:** 不要なコストを避けるため、アプリを使用しなくなった場合は、ポータルでリソースグループを削除するか、`azd down` を実行して削除してください。

<br /><br />
<h2><img src="./documents/Images/ReadMe/business-scenario.png" width="48" />
ビジネスシナリオ
</h2>

|![image](./documents/Images/ReadMe/ui.png)|
|---|

r/>

サンプルデータは、このアクセラレータが様々な業界の営業分析シナリオでどのように使用できるかを示しています。
このシナリオでは、組織が営業調査のためにトップパフォーマンス製品を分析しています。以前は、営業アナリストはデータサイロ全体に散在する異種の営業データと顧客データを手作業で調べる必要がありました。このソリューションアクセラレータを活用することで、アナリストは Microsoft Fabric の統合データにアクセスし、顧客と営業パフォーマンスデータの包括的なビューを得られるようになりました。この機能により、アナリストはデータを照会できます（例: 「前年比で最も収益成長が高い顧客セグメントはどれか」、「人口統計別のトップパフォーマンス製品は何か」）。

⚠️ このリポジトリで使用されているサンプルデータは合成的に生成されたものです。データはサンプルデータとしてのみ使用することを目的としています。

### ビジネス価値

<details>
  <summary>このソリューションが提供する価値について詳しく見る</summary>
<br/>

- **インテリジェントなデータインタラクション**
企業独自のデータを理解し、自然言語の質問をデータ駆動の回答のための自動クエリに変換する会話エージェントを実現。指示を使用してエージェントをトレーニングし、可視性を獲得
- **インサイトと生産性の加速**
インテリジェントなデータ準備、シームレスな統合、AI ガイド付き探索により迅速なインサイトにアクセス。データを分析・強化してトレンドを発見し、ワークフローを自動化し、アイデアをスケーラブルな Agentic ソリューションに変換

- **ガバナンス、スケーラブル、信頼性の高いデータ**
堅牢なガバナンスとメタデータを通じて実用的なインサイトを提供。統合プラットフォームで高品質なデータへの安全なセルフサービスアクセスにより、意思決定、運用効率を改善し、コストを削減

</details>

### ユースケース

<details>
  <summary>このソリューションが提供するユースケースについて詳しく見る</summary>
<br/>

  | **ユースケース** | **ペルソナ** | **課題** | **概要/アプローチ** |
  |---|---|---|---|
  | 営業分析・製品パフォーマンス | 営業アナリスト | 切り離されたデータサイロを検索するために多大な時間を費やし、完全な営業、製品、顧客情報に迅速かつ正確にアクセスすることが困難 | 自然言語を通じて顧客、製品、営業データの包括的なビューを提供。複雑なレポートやダッシュボードをナビゲートせずに迅速にインサイトを取得 |
  顧客ミーティングの改善、クライアントミーティングの準備 | アカウントマネージャー | 手動プロセスと分断されたシステムが日常業務を遅らせ、インサイトの発見を困難にし、パーソナライズされた顧客インタラクションを制限し、解約率の上昇と満足度の低下を招く | ワークフロー内で顧客データを提供し、自然言語クエリを通じて実用的なインサイトを発見し、インタラクションをパーソナライズして解約を減らし、顧客満足度を向上 |

</details>

<br /><br />

<h2><img src="./documents/Images/ReadMe/supporting-documentation.png" width="48" />
関連ドキュメント
</h2>

### セキュリティガイドライン

このソリューションは、ローカル開発および本番デプロイ時に Azure リソースへの安全なアクセスのために[マネージド ID](https://learn.microsoft.com/ja-jp/entra/identity/managed-identities-azure-resources/overview)を使用し、ハードコードされた資格情報の必要性を排除しています。

強力なセキュリティプラクティスを維持するために、このソリューションを基に構築された GitHub リポジトリでは、誤った秘密情報の公開を検出するために [GitHub シークレットスキャン](https://docs.github.com/ja/code-security/secret-scanning/about-secret-scanning)を有効にすることを推奨します。

追加のセキュリティ考慮事項:

- Azure リソースの監視と保護のために [Microsoft Defender for Cloud](https://learn.microsoft.com/ja-jp/azure/defender-for-cloud) を有効化
- 不正アクセスから Azure App Service を保護するために[仮想ネットワーク](https://learn.microsoft.com/ja-jp/azure/app-service/networking-features)または[ファイアウォールルール](https://learn.microsoft.com/ja-jp/azure/app-service/app-service-ip-restrictions)を使用

<br/>

### 関連リファレンス

類似のソリューションアクセラレータをチェック

| ソリューションアクセラレータ | 説明 |
|---|---|
| [Fabric&nbsp;による&nbsp;統合&nbsp;データ&nbsp;基盤](https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator) | Microsoft Fabric、Microsoft Purview、Azure Databricks を活用した統合データアーキテクチャにより、統一された、統合された、ガバナンスされた分析プラットフォームを提供する統合データ基盤 |

<br/>
<https://aka.ms/exporting>

## フィードバック

質問がある、バグを見つけた、または機能をリクエストしたい場合は、このリポジトリで[新しい Issue を送信](https://github.com/naoki1213mj/hackathon202601-stu-se-agentic-ai/issues)してください。

元の Solution Accelerator に関する Issue は [microsoft/agentic-applications-for-unified-data-foundation-solution-accelerator](https://github.com/microsoft/agentic-applications-for-unified-data-foundation-solution-accelerator/issues) へお願いします。

<br/>

## 責任ある AI 透明性 FAQ

<https://aka.ms/exporting>
このソリューションアクセラレータの責任ある AI 透明性の詳細については、[Transparency FAQ](./TRANSPARENCY_FAQ.md)を参照してください。

<br/>

## 免責事項

本ソフトウェアに、Microsoft 製品またはサービス（Azure サービスを含むがこれに限定されない、総称して「Microsoft 製品およびサービス」）で使用されている、または派生したコンポーネントまたはコードが含まれる限りにおいて、当該 Microsoft 製品およびサービスに適用される製品条項にも準拠する必要があります。本ソフトウェアを管理するライセンスは、Microsoft 製品およびサービスを使用するためのライセンスまたはその他の権利を付与するものではないことを認め、同意するものとします。ライセンスまたは本 ReadMe ファイルの内容は、Microsoft 製品およびサービスの製品条項の条件を上書き、修正、終了、または変更するものではありません。

また、本ソフトウェアに適用されるすべての国内および国際輸出法規を遵守する必要があります。これには、仕向地、エンドユーザー、および最終用途に関する制限が含まれます。輸出制限の詳細については、<https://aka.ms/exporting> をご覧ください。

本ソフトウェアおよび Microsoft 製品およびサービスは、(1) 医療機器として設計、意図、または提供されるものではなく、(2) 専門的な医療アドバイス、診断、治療、または判断の代替として設計または意図されるものではなく、専門的な医療アドバイス、診断、治療、または判断の代替として使用すべきではないことを認めます。お客様は、オンラインサービスのお客様の実装のエンドユーザーに対して、適切な同意、警告、免責事項、および確認を表示および/または取得する責任を単独で負います。

本ソフトウェアは SOC 1 および SOC 2 コンプライアンス監査の対象ではないことを認めます。本ソフトウェアを含む Microsoft テクノロジーおよびそのコンポーネントテクノロジーは、認定金融サービス専門家の専門的なアドバイス、意見、または判断の代替として意図または提供されるものではありません。本ソフトウェアを専門的な金融アドバイスまたは判断の代替または代用として使用しないでください。

本ソフトウェアにアクセスまたは使用することにより、本ソフトウェアがサービスの中断、欠陥、エラー、またはその他の障害が人の死亡または重傷、または物理的または環境的損害（総称して「高リスク使用」）をもたらす可能性のある使用をサポートするために設計または意図されていないこと、および本ソフトウェアの中断、欠陥、エラー、またはその他の障害が発生した場合、人、財産、および環境の安全性が、一般的にまたは特定の業界において合理的、適切、かつ合法的なレベルを下回らないようにすることを認めます。本ソフトウェアにアクセスすることにより、本ソフトウェアの高リスク使用は自己責任で行うことをさらに認めます。

<!-- CI/CD Test: 2026-01-15 23:49:23 -->
