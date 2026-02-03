## デプロイ前のクォータ可用性確認

[English](./QuotaCheck.md) | **日本語**

アクセラレータをデプロイする前に、必要なモデルの**クォータが十分に利用可能**であることを確認してください。
> **最適なパフォーマンスのために、容量を 100k トークンに増やすことをお勧めします。**

### まだログインしていない場合はログイン
```
azd auth login
```

### 📌 デフォルトモデルと容量:
```
gpt-4o:150, gpt-4o-mini:150, gpt-4:150
```
### 📌 デフォルトリージョン:
```
eastus, uksouth, eastus2, northcentralus, swedencentral, westus, westus2, southcentralus, canadacentral
```
### 使用シナリオ:
- パラメータなし → デフォルトのモデルと容量がデフォルトリージョンで確認されます。
- モデルのみ指定 → 指定されたモデルがデフォルトリージョンで確認されます。
- リージョンのみ指定 → デフォルトモデルが指定されたリージョンで確認されます。
- モデルとリージョンの両方を指定 → 指定されたモデルが指定されたリージョンで確認されます。
- `--verbose` を渡す → デバッグとトレーサビリティのための詳細なログ出力を有効にします。
  
### **入力形式**
> パラメータ処理には --models, --regions, --verbose オプションを使用します：

✔️ 詳細ログなしでデフォルトのモデルとリージョンを確認するためにパラメータなしで実行：
   ```
  ./quota_check_params.sh
   ```
✔️ 詳細ログを有効にする：
   ```
  ./quota_check_params.sh --verbose
   ```
✔️ デフォルトリージョンで特定のモデルを確認：
  ```
  ./quota_check_params.sh --models gpt-4o:150
  ```
✔️ 特定のリージョンでデフォルトモデルを確認：
  ```
./quota_check_params.sh --regions eastus,westus
  ```
✔️ モデルとリージョンの両方を渡す：
  ```
  ./quota_check_params.sh --models gpt-4o:150 --regions eastus,westus2
  ```
✔️ すべてのパラメータを組み合わせる：
  ```
 ./quota_check_params.sh --models gpt-4:150,gpt-4o-mini:150 --regions eastus,westus --verbose
  ```

### **サンプル出力**
最終テーブルには、利用可能なクォータがあるリージョンがリストされます。これらのリージョンのいずれかをデプロイに選択できます。

![quota-check-output](Images/quota-check-output.png)

---
### **Azure ポータルと Cloud Shell を使用する場合**

1. [Azure ポータル](https://portal.azure.com)に移動します。
2. 右上のナビゲーションメニューで **Azure Cloud Shell** をクリックします。
3. 要件に基づいて適切なコマンドを実行します：

   **デプロイのクォータを確認するには**

    ```sh
    curl -L -o quota_check_params.sh "https://raw.githubusercontent.com/microsoft/Conversation-Knowledge-Mining-Solution-Accelerator/main/infra/scripts/quota_check_params.sh"
    chmod +x quota_check_params.sh
    ./quota_check_params.sh
    ```
    - 詳細なコマンドについては[入力形式](#入力形式)を参照してください。
      
### **VS Code または Codespaces を使用する場合**
1. VS Code または Codespaces でターミナルを開きます。
2. VS Code を使用している場合は、ターミナルウィンドウの右側にあるドロップダウンをクリックし、`Git Bash` を選択します。
   ![git_bash](Images/git_bash.png)
3. スクリプトファイルがある `scripts` フォルダに移動し、スクリプトを実行可能にします：
   ```sh
    cd infra/scripts
    chmod +x quota_check_params.sh
    ```
4. 要件に基づいて適切なスクリプトを実行します：

   **デプロイのクォータを確認するには**

    ```sh
    ./quota_check_params.sh
    ```
   - 詳細なコマンドについては[入力形式](#入力形式)を参照してください。

5. `_bash: az: command not found_` エラーが表示された場合は、Azure CLI をインストールします：

    ```sh
    curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
    az login
    ```
6. Azure CLI をインストールした後、スクリプトを再実行します。
