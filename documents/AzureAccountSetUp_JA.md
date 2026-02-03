## Azure アカウントセットアップ

[English](./AzureAccountSetUp.md) | **日本語**

1. [無料の Azure アカウント](https://azure.microsoft.com/ja-jp/free/)にサインアップし、Azure サブスクリプションを作成します。
2. 必要な権限があることを確認します：
    * Azure アカウントには、[ロールベースアクセス制御管理者](https://learn.microsoft.com/ja-jp/azure/role-based-access-control/built-in-roles#role-based-access-control-administrator-preview)、[ユーザーアクセス管理者](https://learn.microsoft.com/ja-jp/azure/role-based-access-control/built-in-roles#user-access-administrator)、または[所有者](https://learn.microsoft.com/ja-jp/azure/role-based-access-control/built-in-roles#owner)などの `Microsoft.Authorization/roleAssignments/write` 権限が必要です。
    * Azure アカウントには、サブスクリプションレベルで `Microsoft.Resources/deployments/write` 権限も必要です。

以下の手順でアカウントとサブスクリプションの権限を確認できます：
- [Azure ポータル](https://portal.azure.com/)に移動し、「ナビゲーション」の下にある「サブスクリプション」をクリックします
- リストからこのアクセラレータに使用しているサブスクリプションを選択します
    - サブスクリプションを検索しても表示されない場合は、フィルタが選択されていないことを確認してください
- 「アクセス制御 (IAM)」を選択すると、このサブスクリプションに割り当てられているアカウントのロールを確認できます
    - ロールの詳細情報を確認したい場合は、「ロールの割り当て」タブに移動し、アカウント名で検索してから、詳細情報を確認したいロールをクリックします
