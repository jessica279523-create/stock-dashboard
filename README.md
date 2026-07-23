# 我的台股每日簡報

用 GitHub Actions 每天自動抓取台股數據,產生一個屬於妳自己的每日更新網站。

## 設定步驟

### 1. 建立 GitHub Repository
1. 登入 github.com,右上角「+」→「New repository」
2. Repository name 填 `stock-dashboard`(或妳喜歡的名字)
3. 選 **Public**(GitHub Pages 免費方案需要 Public repo)
4. 不要勾選 "Add a README file",直接點 **Create repository**

### 2. 上傳這個資料夾裡的所有檔案
把這個資料夾裡的所有檔案與資料夾(包含隱藏的 `.github` 資料夾)上傳到剛建立的 repo:
- 方法一(網頁版,最簡單):進到 repo 頁面 → "uploading an existing file" → 把檔案拖進去。
  - 注意:網頁上傳工具有時候不會保留 `.github/workflows/update.yml` 的路徑結構,建議改用方法二。
- 方法二(推薦,用 GitHub Desktop):
  1. 下載安裝 [GitHub Desktop](https://desktop.github.com/)
  2. 用妳的 GitHub 帳號登入
  3. "Clone a repository" → 選妳剛建立的 `stock-dashboard`
  4. 把這個資料夾裡的所有檔案複製到 Desktop 幫妳建立的本機資料夾裡
  5. 回到 GitHub Desktop,會看到所有變更,填寫 commit 訊息(例如「初始設定」),點擊 "Commit to main"
  6. 點擊右上角 "Push origin"

### 3. 開啟 GitHub Pages
1. 進到 repo 頁面 → 上方選單 **Settings**
2. 左側選單找到 **Pages**
3. "Build and deployment" → Source 選 **Deploy from a branch**
4. Branch 選 **main**,資料夾選 **/docs**,點 **Save**
5. 等 1-2 分鐘,畫面會顯示妳的網址,例如:
   `https://妳的帳號.github.io/stock-dashboard/`

### 4. 手動測試自動更新
1. 進到 repo 頁面 → 上方選單 **Actions**
2. 左側選 **Update Stock Dashboard**
3. 右側點 **Run workflow** → 綠色按鈕 **Run workflow**
4. 等 1-2 分鐘,重新整理,應該會看到執行成功(綠色勾勾)
5. 打開妳的網址,應該就能看到最新數據了

之後它會依照 `.github/workflows/update.yml` 裡設定的時間(台北時間每個交易日下午 2:10),自動抓最新數據並更新網站,不需要妳做任何事。

## 之後想調整持股或監控清單怎麼辦?
打開 `fetch_and_render.py`,修改最上面的 `HOLDINGS`(持股)和 `WATCHLIST`(監控清單)這兩個區塊,存檔後上傳(push)到 GitHub 就會生效。

## 之後想調整更新時間怎麼辦?
打開 `.github/workflows/update.yml`,修改 `cron: "10 6 * * 1-5"` 這一行。
時間格式是 UTC 時間,台北時間 = UTC + 8 小時。

## 資料來源說明
- **個股報價**:優先使用「台灣證券交易所官方即時報價 API」(mis.twse.com.tw),免費、不需金鑰,是交易所官網本身在用的資料源,比較穩定。若抓不到(例如代碼是上櫃股票判斷錯誤),會自動退回 yfinance 當備援。
- **大盤指數**(加權指數、櫃檯指數):使用 yfinance(`^TWII` / `^TWOII`)。
- 這些都是公開數據,可能會有些微延遲,僅供個人參考學習,不構成投資建議。
- 若某檔股票長期抓不到資料(顯示 `--`),歡迎跟 Claude 說一聲,可以個別排查是代碼問題還是資料源問題。
