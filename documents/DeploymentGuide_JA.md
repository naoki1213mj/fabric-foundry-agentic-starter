# デプロイガイド

[English](./DeploymentGuide.md) | **日本語**

## **前提条件**

このソリューションをデプロイするには、**リソースグループ、リソース、アプリ登録の作成、およびリソースグループレベルでのロール割り当て**に必要な権限を持つ [Azure サブスクリプション](https://azure.microsoft.com/ja-jp/free/)へのアクセスが必要です。これには、サブスクリプションレベルでの共同作成者ロールと、サブスクリプションおよび/またはリソースグループレベルでのロールベースアクセス制御（RBAC）権限が含まれます。[Azure アカウントセットアップ](./AzureAccountSetUp.md)の手順に従ってください。[Fabric 容量セットアップ](https://learn.microsoft.com/ja-jp/fabric/admin/capacity-settings?tabs=fabric-capacity#create-a-new-capacity)の手順に従ってください。

[リージョン別 Azure 製品](https://azure.microsoft.com/ja-jp/explore/global-infrastructure/products-by-region/?products=all&regions=all)ページで、以下のサービスが利用可能な**リージョン**を選択してください：

- [Microsoft Fabric](https://learn.microsoft.com/ja-jp/fabric/)
- [Microsoft Foundry](https://learn.microsoft.com/ja-jp/azure/ai-foundry)
- [GPT モデル容量](https://learn.microsoft.com/ja-jp/azure/ai-services/openai/concepts/models)
- [Azure Container Apps](https://learn.microsoft.com/ja-jp/azure/container-apps/)
- [Azure Container Registry](https://learn.microsoft.com/ja-jp/azure/container-registry/)

サービスが利用可能なリージョンの例：East US、East US2、Australia East、UK South、France Central、Japan East

### **PowerShell ユーザーへの重要な注意**

デジタル署名されていないポリシーにより PowerShell スクリプトの実行で問題が発生した場合、管理者権限の PowerShell セッションで以下のコマンドを実行して `ExecutionPolicy` を一時的に調整できます：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

これにより、システムのポリシーを永続的に変更することなく、現在のセッションでスクリプトを実行できます。

## デプロイオプションと手順

### Fabric デプロイ
1. [Fabric デプロイ](./Fabric_deployment.md)の手順に従って Fabric ワークスペースを作成します

以下のオプションから選択して、GitHub Codespaces、VS Code Dev Containers、VS Code (Web)、ローカル環境、Bicep デプロイの詳細な手順をご確認ください。

| [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/naoki1213mj/hackathon202601-stu-se-agentic-ai) | [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/naoki1213mj/hackathon202601-stu-se-agentic-ai) |
|---|---|

<details>
  <summary><b>GitHub Codespaces でデプロイ</b></summary>

### GitHub Codespaces

GitHub Codespaces を使用してこのソリューションを実行できます。ボタンをクリックすると、ブラウザ内で Web ベースの VS Code インスタンスが開きます：

1. ソリューションアクセラレータを開く（数分かかる場合があります）：

    [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/naoki1213mj/hackathon202601-stu-se-agentic-ai)

2. Codespaces 作成ページでデフォルト値を受け入れます。
3. ターミナルウィンドウが開いていない場合は開きます。
4. [デプロイ手順](#azd-によるデプロイ)に進みます。

</details>

<details>
  <summary><b>VS Code でデプロイ</b></summary>

### VS Code Dev Containers

VS Code Dev Containers でこのソリューションを実行できます。[Dev Containers 拡張機能](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)を使用してローカルの VS Code でプロジェクトが開きます：

1. Docker Desktop を起動します（インストールされていない場合はインストール）。
2. プロジェクトを開く：

    [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/naoki1213mj/hackathon202601-stu-se-agentic-ai)

3. 開いた VS Code ウィンドウで、プロジェクトファイルが表示されたら（数分かかる場合があります）、ターミナルウィンドウを開きます。
4. [デプロイ手順](#azd-によるデプロイ)に進みます。

</details>

<details>
  <summary><b>Visual Studio Code (Web) でデプロイ</b></summary>

### Visual Studio Code (Web)

VS Code Web でこのソリューションを実行できます。ボタンをクリックすると、ブラウザ内で Web ベースの VS Code インスタンスが開きます：

1. ソリューションアクセラレータを開く（数分かかる場合があります）：

    [![Open in Visual Studio Code Web](https://img.shields.io/static/v1?style=for-the-badge&label=Visual%20Studio%20Code%20(Web)&message=Open&color=blue&logo=visualstudiocode&logoColor=white)](https://vscode.dev/azure/?vscode-azure-exp=foundry&agentPayload=eyJiYXNlVXJsIjogImh0dHBzOi8vcmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbS9taWNyb3NvZnQvYWdlbnRpYy1hcHBsaWNhdGlvbnMtZm9yLXVuaWZpZWQtZGF0YS1mb3VuZGF0aW9uLXNvbHV0aW9uLWFjY2VsZXJhdG9yL3JlZnMvaGVhZHMvbWFpbi9pbmZyYS92c2NvZGVfd2ViIiwgImluZGV4VXJsIjogIi9pbmRleC5qc29uIiwgInZhcmlhYmxlcyI6IHsiYWdlbnRJZCI6ICIiLCAiY29ubmVjdGlvblN0cmluZyI6ICIiLCAidGhyZWFkSWQiOiAiIiwgInVzZXJNZXNzYWdlIjogIiIsICJwbGF5Z3JvdW5kTmFtZSI6ICIiLCAibG9jYXRpb24iOiAiIiwgInN1YnNjcmlwdGlvbklkIjogIiIsICJyZXNvdXJjZUlkIjogIiIsICJwcm9qZWN0UmVzb3VyY2VJZCI6ICIiLCAiZW5kcG9pbnQiOiAiIn0sICJjb2RlUm91dGUiOiBbImFpLXByb2plY3RzLXNkayIsICJweXRob24iLCAiZGVmYXVsdC1henVyZS1hdXRoIiwgImVuZHBvaW50Il19)

2. プロンプトが表示されたら、Azure サブスクリプションにリンクされた Microsoft アカウントでサインインします。
3. 適切なサブスクリプションを選択して続行します。

4. ソリューションが開くと、**AI Foundry ターミナル**が自動的に以下のコマンドを実行して必要な依存関係をインストールします：
    ```shell
    sh install.sh
    ```
    このプロセス中に、以下のメッセージが表示されます：
    ```
    What would you like to do with these files?
    - Overwrite with versions from template
    - Keep my existing files unchanged
    ```
    「**Overwrite with versions from template**」を選択し、プロンプトが表示されたら一意の環境名を入力します。

5. **Azure で認証**（VS Code Web ではデバイスコード認証が必要）：
   
    ```shell
    az login --use-device-code
    ```
    > **注意:** VS Code Web 環境では、通常の `az login` コマンドが失敗する場合があります。`--use-device-code` フラグを使用してデバイスコードフローで認証してください。ターミナルのプロンプトに従って認証を完了します。
 
6. [デプロイ手順](#azd-によるデプロイ)に進みます。

</details>

<details>
  <summary><b>ローカル環境でデプロイ</b></summary>

### ローカル環境

上記のオプションを使用しない場合は、以下を準備する必要があります：

1. 以下のツールがインストールされていることを確認：
    - [PowerShell](https://learn.microsoft.com/ja-jp/powershell/scripting/install/installing-powershell?view=powershell-7.5) <small>(v7.0以上)</small> - Windows、macOS、Linux で利用可能
    - [Azure Developer CLI (azd)](https://aka.ms/install-azd) <small>(v1.15.0以上)</small>
    - [Python 3.9以上](https://www.python.org/downloads/)
    - [Docker Desktop](https://www.docker.com/products/docker-desktop/)
    - [Git](https://git-scm.com/downloads)
    - [Microsoft ODBC Driver 17](https://learn.microsoft.com/ja-jp/sql/connect/odbc/download-odbc-driver-for-sql-server?view=sql-server-ver16)

2. リポジトリをクローンするか、コマンドラインでプロジェクトコードをダウンロード：

    ```shell
    # このカスタマイズプロジェクトの場合:
    git clone https://github.com/naoki1213mj/hackathon202601-stu-se-agentic-ai.git
    cd hackathon202601-stu-se-agentic-ai
    
    # またはオリジナル Solution Accelerator の場合:
    # azd init -t microsoft/agentic-applications-for-unified-data-foundation-solution-accelerator/
    ```

3. ターミナルまたはエディタでプロジェクトフォルダを開きます。
4. [デプロイ手順](#azd-によるデプロイ)に進みます。

</details>

<br/>

デプロイ時に以下の設定を変更できます：

<details>
  <summary><b>設定可能なデプロイ設定</b></summary>

デプロイを開始すると、ほとんどのパラメータには**デフォルト値**がありますが、[こちら](../documents/CustomizingAzdParameters.md)で以下の設定を更新できます：

| **設定** | **説明** | **デフォルト値** |
| -------- | -------- | -------------- |
| **Azure リージョン** | リソースが作成されるリージョン | *(空)* |
| **環境名** | リソースのプレフィックスに使用される一意の ID を生成するための **3〜20文字の英数字** | env\_name |
| **バックエンドプログラミング言語** | バックエンド API のプログラミング言語: **python** または **dotnet** | *(空)* |
| **ユースケース** | ユースケース: **Retail-sales-analysis** または **Insurance-improve-customer-meetings** | *(空)* |
| **デプロイタイプ** | ドロップダウンから選択（許可値: `Standard`, `GlobalStandard`） | GlobalStandard |
| **GPT モデル** | **gpt-4, gpt-4o, gpt-4o-mini** から選択 | gpt-4o-mini |
| **GPT モデルバージョン** | 選択した GPT モデルのバージョン | 2024-07-18 |
| **OpenAI API バージョン** | 使用する Azure OpenAI API バージョン | 2025-01-01-preview |
| **GPT モデルデプロイ容量** | **GPT モデル**の容量を設定（千単位） | 30k |
| **イメージタグ** | デプロイする Docker イメージタグ。一般的な値: `latest`, `dev`, `hotfix` | latest |
| **ローカルビルドを使用** | ローカルコンテナビルドを使用するかどうかのブールフラグ | false |
| **既存の Log Analytics ワークスペース** | 既存の Log Analytics ワークスペース ID を再利用 | *(空)* |
| **既存の Microsoft Foundry プロジェクト** | 新規作成せずに既存の Microsoft Foundry プロジェクト ID を再利用 | *(空)* |

</details>

<details>
  <summary><b>[オプション] クォータ推奨事項</b></summary>

デフォルトでは、デプロイ時の **GPT-4o-mini モデル容量**は **30k トークン**に設定されているため、以下の更新を推奨します：

> **Global Standard | GPT-4o-mini の場合 - デプロイ後に最適なパフォーマンスのために容量を少なくとも 150k トークンに増やしてください。**

サブスクリプションのクォータと容量に応じて、[クォータ設定を調整](AzureGPTQuotaSettings.md)して特定のニーズに対応できます。追加の最適化のために[デプロイパラメータを調整](CustomizingAzdParameters.md)することもできます。

**⚠️ 警告:** クォータが不足するとデプロイエラーが発生する可能性があります。このソリューションをデプロイする前に、推奨容量があるか、追加容量をリクエストしてください。

</details>

<details>
  <summary><b>既存の Log Analytics ワークスペースの再利用</b></summary>

  [既存のワークスペース ID を取得するガイド](/documents/re-use-log-analytics.md)

</details>

<details>
  <summary><b>既存の Microsoft Foundry プロジェクトの再利用</b></summary>

  [既存のプロジェクト ID を取得するガイド](/documents/re-use-foundry-project.md)

</details>

### AZD によるデプロイ

[Codespaces](#github-codespaces)、[Dev Containers](#vs-code-dev-containers)、[Visual Studio Code (Web)](#visual-studio-code-web)、または[ローカル](#ローカル環境)でプロジェクトを開いたら、以下の手順で Azure にデプロイできます：

1. Azure にログイン：

    ```shell
    azd auth login
    ```

    #### **テナント ID** を使用して Azure Developer CLI (`azd`) で認証するには、以下のコマンドを使用：

    ```sh
    azd auth login --tenant-id <tenant-id>
    ```

2. すべてのリソースをプロビジョニングしてデプロイ：

    ```shell
    azd up
    ```

3. `azd` 環境名を入力します（例: "daapp"）。
4. Azure アカウントからサブスクリプションを選択し、すべてのリソースのクォータがあるロケーションを選択します。
5. バックエンド API のプログラミング言語を選択：
   - **Python**
   - **.NET (dotnet)**
6. ユースケースを選択：
   - **Retail-sales-analysis**
   - **Insurance-improve-customer-meetings**

   このデプロイには、アカウントにリソースをプロビジョニングし、サンプルデータでソリューションをセットアップするのに *7〜10分* かかります。
   
   デプロイ中にエラーまたはタイムアウトが発生した場合、リソースの可用性制約がある可能性があるため、ロケーションを変更すると解決することがあります。

7. デプロイが正常に完了したら、ターミナルから 2 つの bash コマンドをコピーします（例: 
`bash ./infra/scripts/agent_scripts/run_create_agents_scripts.sh` と
`bash ./infra/scripts/fabric_scripts/run_fabric_items_scripts.sh <fabric-workspaceId>`）。

> **注意**: GitHub Codespaces、VS Code Dev Container、または Visual Studio Code (Web) でこのデプロイを実行している場合は、ステップ 9 にスキップしてください。

8. 仮想環境を作成してアクティブ化
  
    ```shell
    python -m venv .venv
    ```

    ```shell
    source .venv/Scripts/activate
    ```

9. Azure にログイン
    ```shell
    az login
    ```

    または、デバイスコードを使用して Azure にログイン（VS Code Web 使用時に推奨）：

    ```shell
    az login --use-device-code
    ```

> **注意**: ステップ 10 と 11 を完了するには Git Bash ターミナルを開く必要があります。

10. azd デプロイの出力から bash スクリプトを実行します。スクリプトは以下のようになります：
    
    ```Shell
    bash ./infra/scripts/agent_scripts/run_create_agents_scripts.sh
    ```
    azd env がない場合は、コマンドにパラメータを渡す必要があります：
    ```Shell
    bash ./infra/scripts/agent_scripts/run_create_agents_scripts.sh <project-endpoint> <solution-name> <gpt-model-name> <ai-foundry-resource-id> <api-app-name> <resource-group>
    ```

11. azd デプロイの出力から bash スクリプトを実行します。`<fabric-workspaceId>` を前のステップで作成した Fabric ワークスペース ID に置き換えます：
    ```Shell
    bash ./infra/scripts/fabric_scripts/run_fabric_items_scripts.sh <fabric-workspaceId>
    ```

    azd env がない場合は、コマンドにパラメータを渡す必要があります：
    ```Shell
    bash ./infra/scripts/fabric_scripts/run_fabric_items_scripts.sh <fabric-workspaceId> <solutionname> <ai-foundry-name> <backend-api-mid-principal> <backend-api-mid-client> <api-app-name> <resourcegroup>
    ```

12. スクリプトが正常に実行されたら、デプロイされたリソースグループに移動し、App Service を見つけて、`Default domain` からアプリ URL を取得します。

13. アプリケーションの試用が完了したら、`azd down` を実行してリソースを削除できます。


## デプロイ後の手順

1. **アプリ認証の追加**
   
    [アプリ認証](./AppAuthentication.md)の手順に従って、App Service で認証を構成します。注意：認証の変更が反映されるまで最大 10 分かかる場合があります。

2. **失敗したデプロイ後のリソース削除**

     - デプロイが失敗した場合やリソースをクリーンアップする必要がある場合は、[リソースグループの削除](./DeleteResourceGroup.md)の手順に従ってください。

3. **Fabric リソースのクリーンアップ**

     アクセラレータの試用が完了し、Fabric リソース（レイクハウス、SQL データベース、ロール割り当て）をクリーンアップしたい場合は、以下のスクリプトを実行します：

     ```shell
     bash ./infra/scripts/fabric_scripts/delete_fabric_items_scripts.sh <fabric-workspaceId>
     ```

     azd env がない場合は、コマンドにパラメータを渡す必要があります：
     
     ```shell
     bash ./infra/scripts/fabric_scripts/delete_fabric_items_scripts.sh <fabric-workspaceId> <solutionname> <backend-api-principal-id>
     ```

     **注意**: このスクリプトは、Fabric ワークスペースからレイクハウス、SQL データベース、およびサービスプリンシパルロール割り当てを削除します。すべての Azure リソースを完全に削除するには、`azd down` を使用してください。

## サンプル質問

アプリで尋ねることができる**サンプル質問**を以下に示します：

Retail sales analysis ユースケースの場合：
- 過去 5 年間の年別総売上を折れ線グラフで表示してください。
- 昨年の売上上位 10 製品を表で表示してください。
- ドーナツチャートで表示してください。

Insurance improve customer meetings ユースケースの場合：
- Ida Abolina との会議があります。彼女の顧客情報を要約し、請求、支払い、コミュニケーションの数を教えてください。
- 彼女のコミュニケーションの詳細を教えてください。
- Ida のポリシーデータに基づいて、支払いを逃したことはありますか？

これらの質問は、データからインサイトを探索するための出発点として最適です。

## Fabric Data Agent を作成して Teams に公開
1. [CopilotStudioDeployment](./CopilotStudioDeployment.md)の手順に従ってください。

## ローカル開発
ローカル開発用にアプリケーションをセットアップして実行するには、[ローカル開発セットアップガイド](./LocalDevelopmentSetup_JA.md)を参照してください。
