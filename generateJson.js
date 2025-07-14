// --- グローバルヘルパー関数 ---

// 特定ディレクトリを取得・作成するヘルパー関数
function getTargetDirectory() {
  var targetConfig = getConfig('file_management.target_directory');
  
  // 特定ディレクトリが無効な場合はnullを返す
  if (!targetConfig || !targetConfig.enabled) {
    return null;
  }
  
  var folder = null;
  
  // フォルダIDが指定されている場合はIDで検索
  if (targetConfig.folder_id && targetConfig.folder_id.trim() !== '') {
    try {
      folder = DriveApp.getFolderById(targetConfig.folder_id);
      Logger.log('📁 指定されたフォルダIDでフォルダを取得: ' + folder.getName());
      return folder;
    } catch (error) {
      Logger.log('⚠️ 指定されたフォルダIDが見つかりません: ' + targetConfig.folder_id);
    }
  }
  
  // フォルダ名で検索
  var folders = DriveApp.getFoldersByName(targetConfig.folder_name);
  if (folders.hasNext()) {
    folder = folders.next();
    Logger.log('📁 既存のフォルダを取得: ' + folder.getName());
    return folder;
  }
  
  // フォルダが存在せず、作成が許可されている場合は作成
  if (targetConfig.create_if_not_exists) {
    folder = DriveApp.createFolder(targetConfig.folder_name);
    Logger.log('📁 新しいフォルダを作成: ' + folder.getName());
    return folder;
  }
  
  Logger.log('⚠️ 指定されたフォルダが見つからず、作成も許可されていません: ' + targetConfig.folder_name);
  return null;
}

// 全月データ用ディレクトリを取得・作成するヘルパー関数
function getAllPeriodDirectory() {
  var allPeriodConfig = getConfig('file_management.all_period_directory');
  
  // 全月データ用ディレクトリが無効な場合はnullを返す
  if (!allPeriodConfig || !allPeriodConfig.enabled) {
    return null;
  }
  
  var folder = null;
  
  // フォルダIDが指定されている場合はIDで検索
  if (allPeriodConfig.folder_id && allPeriodConfig.folder_id.trim() !== '') {
    try {
      folder = DriveApp.getFolderById(allPeriodConfig.folder_id);
      Logger.log('📁 指定されたフォルダIDで全月データフォルダを取得: ' + folder.getName());
      return folder;
    } catch (error) {
      Logger.log('⚠️ 指定された全月データフォルダIDが見つかりません: ' + allPeriodConfig.folder_id);
    }
  }
  
  // フォルダ名で検索
  var folders = DriveApp.getFoldersByName(allPeriodConfig.folder_name);
  if (folders.hasNext()) {
    folder = folders.next();
    Logger.log('📁 既存の全月データフォルダを取得: ' + folder.getName());
    return folder;
  }
  
  // フォルダが存在せず、作成が許可されている場合は作成
  if (allPeriodConfig.create_if_not_exists) {
    folder = DriveApp.createFolder(allPeriodConfig.folder_name);
    Logger.log('📁 新しい全月データフォルダを作成: ' + folder.getName());
    return folder;
  }
  
  Logger.log('⚠️ 指定された全月データフォルダが見つからず、作成も許可されていません: ' + allPeriodConfig.folder_name);
  return null;
}

// ファイルを特定ディレクトリに保存するヘルパー関数（重複削除機能付き）
function saveFileToTargetDirectory(fileName, jsonData) {
  var targetFolder = getTargetDirectory();
  
  if (targetFolder) {
    // 既存の同名ファイルを削除
    try {
      var existingFiles = targetFolder.getFilesByName(fileName);
      while (existingFiles.hasNext()) {
        var existingFile = existingFiles.next();
        existingFile.setTrashed(true);
        Logger.log('🗑️ 既存ファイル削除: ' + existingFile.getName());
      }
    } catch (error) {
      Logger.log('⚠️ 既存ファイル削除エラー: ' + error.message);
    }
    
    var blob = Utilities.newBlob(jsonData, 'application/json', fileName);
    var file = targetFolder.createFile(blob);
    Logger.log('✅ ファイルを特定ディレクトリに保存: ' + file.getName() + ' - ' + file.getUrl());
    return file;
  } else {
    // 特定ディレクトリが設定されていない場合は従来通りマイドライブに保存
    // マイドライブでも同名ファイルを削除
    try {
      var existingFiles = DriveApp.getFilesByName(fileName);
      while (existingFiles.hasNext()) {
        var existingFile = existingFiles.next();
        existingFile.setTrashed(true);
        Logger.log('🗑️ 既存ファイル削除（マイドライブ）: ' + existingFile.getName());
      }
    } catch (error) {
      Logger.log('⚠️ 既存ファイル削除エラー（マイドライブ）: ' + error.message);
    }
    
    var blob = Utilities.newBlob(jsonData, 'application/json', fileName);
    var file = DriveApp.createFile(blob);
    Logger.log('✅ ファイルをマイドライブに保存: ' + file.getName() + ' - ' + file.getUrl());
    return file;
  }
}

// ファイルを全月データ用ディレクトリに保存するヘルパー関数（統一：インサイドセールス分析データフォルダを使用）
function saveFileToAllPeriodDirectory(fileName, jsonData) {
  // 全月データも「インサイドセールス分析データ」フォルダに統一
  Logger.log('📁 全月データを「インサイドセールス分析データ」フォルダに統一保存: ' + fileName);
  return saveFileToTargetDirectory(fileName, jsonData);
}

function fixOutlierDate(dateStr) {
  if (!dateStr) return dateStr;
  var d = new Date(dateStr);
  if (d.getFullYear() < 2010) {
    // 年が明らかに古い場合は現在の年に補正
    var now = new Date();
    d.setFullYear(now.getFullYear());
    return d.toISOString();
  }
  return dateStr;
}

function mergeSalesDataNested() {
  // ヘルパー関数: 安全な日時変換
  function safeDateConversion(dateValue) {
    if (!dateValue) return null;
    
    try {
      // 文字列の場合はDateオブジェクトに変換
      if (typeof dateValue === 'string') {
        // 空文字列や無効な文字列の場合はnullを返す
        if (dateValue.trim() === '') return null;
        
        // 日本語の日付形式に対応
        var dateStr = dateValue.toString().trim();
        
        // 2024/10/07 形式の場合
        if (/^\d{4}\/\d{1,2}\/\d{1,2}$/.test(dateStr)) {
          return new Date(dateStr).toISOString();
        }
        
        // 2024/10/08 19:22:46 形式の場合
        if (/^\d{4}\/\d{1,2}\/\d{1,2}\s+\d{1,2}:\d{1,2}:\d{1,2}$/.test(dateStr)) {
          return new Date(dateStr).toISOString();
        }
        
        // その他の形式は標準のDateコンストラクタで試行
        var date = new Date(dateStr);
        if (isNaN(date.getTime())) return null;
        return date.toISOString();
      }
      
      // Dateオブジェクトの場合はそのままISO文字列に変換
      if (dateValue instanceof Date) {
        if (isNaN(dateValue.getTime())) return null;
        return dateValue.toISOString();
      }
      
      return null;
    } catch (e) {
      Logger.log('日時変換エラー: ' + dateValue + ' - ' + e.message);
      return null;
    }
  }

  // ヘルパー関数: 数値変換
  function safeNumber(value) {
    if (value === null || value === undefined || value === '') return 0;
    var num = parseFloat(value);
    return isNaN(num) ? 0 : num;
  }

  // 1) スプレッドシートを開く
  var SPREADSHEET_ID = '1tZDpkzCCYTgeq1NqSFHr9HB-1J3VUMw3vncKCrhUOqU';
  var ss = SpreadsheetApp.openById(SPREADSHEET_ID);

  // 2) StaffMaster シート読み込み → joinMap 作成
  var staffSheet = ss.getSheetByName('スタッフ一覧');
  var staffData  = staffSheet.getDataRange().getValues();
  var joinMap    = {};
  staffData.forEach(function(row, i) {
    if (i === 0) return; // ヘッダー行をスキップ
    var name     = row[1];           // 列B: スタッフ名
    var joinDate = safeDateConversion(row[2]); // 列C: 入社日
    var branch   = row[3];           // 列D: 支部
    joinMap[name] = joinDate;
  });

  // 3) Sansan却下 読み込み ※Bill One系の却下理由を取得
  var sSheet = ss.getSheetByName('Sansan却下');
  var sRaw   = sSheet.getDataRange().getValues();
  var sHdr   = sRaw.shift();
  var sansanRejections = sRaw.map(function(row) {
    var rec = {};
    sHdr.forEach(function(h,i){ rec[h] = row[i]; });
    return {
      date:    safeDateConversion(rec['発生年月']),
      company: rec['会社名'],
      product: rec['プロダクト'],
      reject_reason: rec['理由'],
      reject_detail: rec['FB詳細'] || rec['却下理由']
    };
  });

  // 4) 新TAAAN商談一覧 読み込み
  var dSheet = ss.getSheetByName('TAAAN商談');
  var dRaw   = dSheet.getDataRange().getValues();
  var dHdr   = dRaw.shift();
  var deals  = dRaw.map(function(row) {
    var rec = {};
    dHdr.forEach(function(h,i){ rec[h] = row[i]; });
    return {
      date:             safeDateConversion(rec['作成日時']),
      staff:            rec['パートナー担当者'],
      company:          rec['メーカー名'],
      product:          rec['プロダクト名'] || rec['サービス名'], // CB列から商材情報を取得、フォールバックとしてサービス名を使用
      commission:       rec['報酬'] || null,
      deal_start:       safeDateConversion(rec['商談開始日時']),
      deal_end:         safeDateConversion(rec['商談終了日時']),
      corporateNumber:  rec['法人番号'],
      corporateName:    rec['会社名'],
      deal_status:      rec['商談ステータス'],
      inline_reason:    rec['却下理由'] || null
    };
  });

  // 5) 日報 シート読み込み (1行目と2行目を組み合わせてヘッダー作成)
  var dailySheet   = ss.getSheetByName('学生日報');
  var lastCol      = dailySheet.getLastColumn();
  
  // 1行目（グループ分け）と2行目（カラム名）を取得
  var groupRow     = dailySheet.getRange(1,1,1,lastCol).getValues()[0];
  var columnRow    = dailySheet.getRange(2,1,1,lastCol).getValues()[0];
  
  // ヘッダーを組み合わせて作成
  var dailyHeaders = [];
  var currentGroup = '';
  
  for (var i = 0; i < lastCol; i++) {
    var group = groupRow[i] || currentGroup;
    var column = columnRow[i];
    
    if (group && group !== currentGroup) {
      currentGroup = group;
    }
    
    if (column) {
      // グループ名をプレフィックスとして追加
      var headerName = currentGroup ? currentGroup + '_' + column : column;
      dailyHeaders.push(headerName);
    } else {
      dailyHeaders.push('');
    }
  }
  
  var dailyRaw = dailySheet.getRange(3,1, dailySheet.getLastRow()-2, lastCol).getValues();
  var daily = dailyRaw.map(function(row, idx) {
    var rec = {};
    dailyHeaders.forEach(function(h,i){ 
      if (h) rec[h] = row[i]; 
    });
    
    // メイン商材のデータを取得
    var mainProduct = rec['メイン商材_新規架電：メイン商材'] || rec['新規架電：メイン商材'];
    var mainCallHours = safeNumber(rec['メイン商材_総荷電時間(単位は●時間)'] || rec['総荷電時間(単位は●時間)']);
    var mainCallCount = safeNumber(rec['メイン商材_架電数　※半角で入力'] || rec['架電数　※半角で入力']);
    var mainReceptionBk = safeNumber(rec['メイン商材_受付BK　※半角で入力'] || rec['受付BK　※半角で入力']);
    var mainNoOneInCharge = safeNumber(rec['メイン商材_担当不在　※半角で入力'] || rec['担当不在　※半角で入力']);
    var mainDisconnect = safeNumber(rec['メイン商材_不通　※半角で入力'] || rec['不通　※半角で入力']);
    var mainChargeConnected = safeNumber(rec['メイン商材_担当コネクト　※半角で入力'] || rec['担当コネクト　※半角で入力']);
    var mainChargeBk = safeNumber(rec['メイン商材_担当BK（見込みも含む）　※半角で入力'] || rec['担当BK（見込みも含む）　※半角で入力']);
    var mainGetAppointment = safeNumber(rec['メイン商材_アポ獲得　※半角で入力'] || rec['アポ獲得　※半角で入力']);
    
    // サブ商材のデータを配列として取得
    var subProducts = [];
    for (var i = 1; i <= 3; i++) {
      var subProductName = rec['サブ商材' + i + '_ルート架電：サブ商材'];
      if (subProductName && subProductName !== '終了') {
        subProducts.push({
          product: subProductName,
          call_hours: safeNumber(rec['サブ商材' + i + '_総荷電時間(単位は●時間)']),
          call_count: safeNumber(rec['サブ商材' + i + '_架電数　※半角で入力']),
          reception_bk: safeNumber(rec['サブ商材' + i + '_受付BK　※半角で入力']),
          no_one_in_charge: safeNumber(rec['サブ商材' + i + '_担当不在　※半角で入力']),
          disconnect: safeNumber(rec['サブ商材' + i + '_不通　※半角で入力']),
          charge_connected: safeNumber(rec['サブ商材' + i + '_担当コネクト（担当BK＋アポ獲得）　※半角で入力']),
          charge_bk: safeNumber(rec['サブ商材' + i + '_担当BK（見込みも含む）　※半角で入力']),
          get_appointment: safeNumber(rec['サブ商材' + i + '_アポ獲得　※半角で入力'])
        });
      }
    }
    
    // 日付補正
    var rawDate = safeDateConversion(rec['今日の日付']);
    var fixedDate = fixOutlierDate(rawDate);
    
    return {
      daily_report_id: idx+1,
      date: fixedDate,
      staff: rec['名前'],
      join_date: joinMap[rec['名前']] || null,
      main_product: {
        product: mainProduct,
        call_hours: mainCallHours,
        call_count: mainCallCount,
        reception_bk: mainReceptionBk,
        no_one_in_charge: mainNoOneInCharge,
        disconnect: mainDisconnect,
        charge_connected: mainChargeConnected,
        charge_bk: mainChargeBk,
        get_appointment: mainGetAppointment
      },
      sub_products: subProducts
    };
  });

  // 6) マージ & ネスト構造で JSON 化
  var output = daily.map(function(d) {
    // helper: 条件にマッチするレコード検索
    function findMatch(arr, keys) {
      return arr.find(function(r) {
        return keys.every(function(k) {
          // 日付の場合は日付部分のみで比較
          if (k === 'date') {
            var d1 = d[k] ? d[k].split('T')[0] : null;
            var d2 = r[k] ? r[k].split('T')[0] : null;
            return d1 === d2;
          }
          return String(d[k]) === String(r[k]);
        });
      });
    }

    // 日報データには会社名の情報がないため、商談・却下データとのマッチングは日付とスタッフ名のみで行う
    var dealRec = findMatch(deals, ['date','staff']);
    var sanRec  = findMatch(sansanRejections, ['date','staff']);

    // 判定：Bill One系を別シートから取得
    var isBillOne = ['Bill One','Bill One経費'].includes(d.main_product.product);

    // company_report 作成
    var companyReport = {
      company_name: null, // 日報データには会社名の情報がない
      product_name: d.main_product.product,
      deal_status: null, // デフォルトはnull
      reason_of_status: {}
    };

    // 商談情報がある場合のみdeal_statusを設定
    if (dealRec) {
      if (dealRec.commission) {
        companyReport.deal_status = '承認';
      } else {
        companyReport.deal_status = '却下';
      }
      
      // 商談情報を追加
      companyReport.deal_info = {
        commission: dealRec.commission,
        deal_start: dealRec.deal_start,
        deal_end: dealRec.deal_end,
        corporate_number: dealRec.corporateNumber,
        corporate_name: dealRec.corporateName,
        deal_status: dealRec.deal_status
      };
    }

    // 却下理由の設定
    if (isBillOne) {
      if (sanRec) {
        companyReport.reason_of_status = {
          reason: sanRec.reject_reason,
          detail: sanRec.reject_detail
        };
      }
    } else {
      // inline sheetの却下理由優先
      if (dealRec && dealRec.inline_reason) {
        companyReport.reason_of_status = {
          reason: dealRec.inline_reason
        };
      }
    }

    return {
      daily_report_id: d.daily_report_id,
      staff: {
        name:      d.staff,
        join_date: d.join_date
      },
      activity_detail: {
        call_report: {
          call_count: d.main_product.call_count,
          call_time:  d.main_product.call_hours
        },
        company_report: companyReport,
        sub_products: d.sub_products
      }
    };
  });

  // 7) JSON 出力
  var json = JSON.stringify(output, null, 2);
  var file = saveFileToAllPeriodDirectory('merged_sales_data.json', json);
  Logger.log('✅ JSON 出力完了: ' + file.getUrl());
}

function generateAnalysisJson() {
  // ヘルパー関数: 安全な日時変換
  function safeDateConversion(dateValue) {
    if (!dateValue) return null;
    
    try {
      if (typeof dateValue === 'string') {
        if (dateValue.trim() === '') return null;
        
        var dateStr = dateValue.toString().trim();
        
        if (/^\d{4}\/\d{1,2}\/\d{1,2}$/.test(dateStr)) {
          return new Date(dateStr).toISOString();
        }
        
        if (/^\d{4}\/\d{1,2}\/\d{1,2}\s+\d{1,2}:\d{1,2}:\d{1,2}$/.test(dateStr)) {
          return new Date(dateStr).toISOString();
        }
        
        var date = new Date(dateStr);
        if (isNaN(date.getTime())) return null;
        return date.toISOString();
      }
      
      if (dateValue instanceof Date) {
        if (isNaN(dateValue.getTime())) return null;
        return dateValue.toISOString();
      }
      
      return null;
    } catch (e) {
      Logger.log('日時変換エラー: ' + dateValue + ' - ' + e.message);
      return null;
    }
  }

  // ヘルパー関数: 月次データの取得
  function getMonthFromDate(dateStr) {
    if (!dateStr) return null;
    return dateStr.substring(0, 7); // YYYY-MM形式
  }

  // ヘルパー関数: 数値変換
  function safeNumber(value) {
    if (value === null || value === undefined || value === '') return 0;
    var num = parseFloat(value);
    return isNaN(num) ? 0 : num;
  }

  // ヘルパー関数: 日付の差分計算（月数）
  function getMonthsBetween(date1, date2) {
    if (!date1 || !date2) return 0;
    var d1 = new Date(date1);
    var d2 = new Date(date2);
    return (d2.getFullYear() - d1.getFullYear()) * 12 + (d2.getMonth() - d1.getMonth());
  }

  // 1) スプレッドシートを開く
  var SPREADSHEET_ID = '1tZDpkzCCYTgeq1NqSFHr9HB-1J3VUMw3vncKCrhUOqU';
  var ss = SpreadsheetApp.openById(SPREADSHEET_ID);

  // 2) スタッフ一覧読み込み
  var staffSheet = ss.getSheetByName('スタッフ一覧');
  var staffData = staffSheet.getDataRange().getValues();
  var staffMap = {};
  staffData.forEach(function(row, i) {
    if (i === 0) return; // ヘッダー行をスキップ
    var name = row[1];           // 列B: スタッフ名
    var joinDate = safeDateConversion(row[2]); // 列C: 入社日
    var branch = row[3];         // 列D: 支部
    staffMap[name] = {
      join_date: joinDate,
      branch: branch
    };
  });

  // 3) Sansan却下読み込み
  var sSheet = ss.getSheetByName('Sansan却下');
  var sRaw = sSheet.getDataRange().getValues();
  var sHdr = sRaw.shift();
  var sansanRejections = sRaw.map(function(row) {
    var rec = {};
    sHdr.forEach(function(h,i){ rec[h] = row[i]; });
    return {
      date: safeDateConversion(rec['発生年月']),
      company: rec['会社名'],
      product: rec['プロダクト'],
      reject_reason: rec['理由'],
      reject_detail: rec['FB詳細'] || rec['却下理由']
    };
  });

  // 4) TAAAN商談読み込み
  var dSheet = ss.getSheetByName('TAAAN商談');
  var dRaw = dSheet.getDataRange().getValues();
  var dHdr = dRaw.shift();
  var deals = dRaw.map(function(row) {
    var rec = {};
    dHdr.forEach(function(h,i){ rec[h] = row[i]; });
    return {
      date: safeDateConversion(rec['商談開始日時']),
      staff: rec['パートナー担当者'],
      company: rec['メーカー名'],
      product: rec['プロダクト名'],
      commission: safeNumber(rec['報酬']),
      deal_start: safeDateConversion(rec['商談開始日時']),
      deal_end: safeDateConversion(rec['商談終了日時']),
      corporateNumber: rec['法人番号'],
      corporateName: rec['会社名'],
      deal_status: rec['商談ステータス'],
      inline_reason: rec['却下理由'] || null
    };
  });

  // 5) 日報読み込み
  var dailySheet = ss.getSheetByName('学生日報');
  var lastCol = dailySheet.getLastColumn();
  
  var groupRow = dailySheet.getRange(1,1,1,lastCol).getValues()[0];
  var columnRow = dailySheet.getRange(2,1,1,lastCol).getValues()[0];
  
  var dailyHeaders = [];
  var currentGroup = '';
  
  for (var i = 0; i < lastCol; i++) {
    var group = groupRow[i] || currentGroup;
    var column = columnRow[i];
    
    if (group && group !== currentGroup) {
      currentGroup = group;
    }
    
    if (column) {
      var headerName = currentGroup ? currentGroup + '_' + column : column;
      dailyHeaders.push(headerName);
    } else {
      dailyHeaders.push('');
    }
  }
  
  var dailyRaw = dailySheet.getRange(3,1, dailySheet.getLastRow()-2, lastCol).getValues();
  var daily = dailyRaw.map(function(row, idx) {
    var rec = {};
    dailyHeaders.forEach(function(h,i){ 
      if (h) rec[h] = row[i]; 
    });
    
    // メイン商材のデータを取得
    var mainProduct = rec['メイン商材_新規架電：メイン商材'] || rec['新規架電：メイン商材'];
    var mainCallHours = safeNumber(rec['メイン商材_総荷電時間(単位は●時間)'] || rec['総荷電時間(単位は●時間)']);
    var mainCallCount = safeNumber(rec['メイン商材_架電数　※半角で入力'] || rec['架電数　※半角で入力']);
    var mainReceptionBk = safeNumber(rec['メイン商材_受付BK　※半角で入力'] || rec['受付BK　※半角で入力']);
    var mainNoOneInCharge = safeNumber(rec['メイン商材_担当不在　※半角で入力'] || rec['担当不在　※半角で入力']);
    var mainDisconnect = safeNumber(rec['メイン商材_不通　※半角で入力'] || rec['不通　※半角で入力']);
    var mainChargeConnected = safeNumber(rec['メイン商材_担当コネクト　※半角で入力'] || rec['担当コネクト　※半角で入力']);
    var mainChargeBk = safeNumber(rec['メイン商材_担当BK（見込みも含む）　※半角で入力'] || rec['担当BK（見込みも含む）　※半角で入力']);
    var mainGetAppointment = safeNumber(rec['メイン商材_アポ獲得　※半角で入力'] || rec['アポ獲得　※半角で入力']);
    
    // サブ商材のデータを配列として取得
    var subProducts = [];
    for (var i = 1; i <= 3; i++) {
      var subProductName = rec['サブ商材' + i + '_ルート架電：サブ商材'];
      if (subProductName && subProductName !== '終了') {
        subProducts.push({
          product: subProductName,
          call_hours: safeNumber(rec['サブ商材' + i + '_総荷電時間(単位は●時間)']),
          call_count: safeNumber(rec['サブ商材' + i + '_架電数　※半角で入力']),
          reception_bk: safeNumber(rec['サブ商材' + i + '_受付BK　※半角で入力']),
          no_one_in_charge: safeNumber(rec['サブ商材' + i + '_担当不在　※半角で入力']),
          disconnect: safeNumber(rec['サブ商材' + i + '_不通　※半角で入力']),
          charge_connected: safeNumber(rec['サブ商材' + i + '_担当コネクト（担当BK＋アポ獲得）　※半角で入力']),
          charge_bk: safeNumber(rec['サブ商材' + i + '_担当BK（見込みも含む）　※半角で入力']),
          get_appointment: safeNumber(rec['サブ商材' + i + '_アポ獲得　※半角で入力'])
        });
      }
    }
    
    // 日付補正
    var rawDate = safeDateConversion(rec['今日の日付']);
    var fixedDate = fixOutlierDate(rawDate);
    
    return {
      date: fixedDate,
      month: getMonthFromDate(fixedDate),
      staff: rec['名前'],
      branch: staffMap[rec['名前']] ? staffMap[rec['名前']].branch : null,
      join_date: staffMap[rec['名前']] ? staffMap[rec['名前']].join_date : null,
      main_product: {
        product: mainProduct,
        call_hours: mainCallHours,
        call_count: mainCallCount,
        reception_bk: mainReceptionBk,
        no_one_in_charge: mainNoOneInCharge,
        disconnect: mainDisconnect,
        charge_connected: mainChargeConnected,
        charge_bk: mainChargeBk,
        get_appointment: mainGetAppointment
      },
      sub_products: subProducts
    };
  });

  // 6) 月次集計データの作成
  var monthlyData = {};
  
  // 日報データを月別にグループ化
  daily.forEach(function(record) {
    if (!record.month) return;
    
    if (!monthlyData[record.month]) {
      monthlyData[record.month] = {
        month: record.month,
        branches: {},
        products: {},
        staff: {},
        summary: {
          total_calls: 0,
          total_hours: 0,
          total_appointments: 0,
          total_deals: 0,
          total_approved: 0,
          total_rejected: 0,
          total_revenue: 0,
          total_potential_revenue: 0
        }
      };
    }
    
    var monthData = monthlyData[record.month];
    
    // 支部別集計
    if (record.branch) {
      if (!monthData.branches[record.branch]) {
        monthData.branches[record.branch] = {
          branch_name: record.branch,
          staff_count: 0,
          total_calls: 0,
          total_hours: 0,
          total_appointments: 0,
          total_deals: 0,
          total_approved: 0,
          total_rejected: 0,
          total_revenue: 0,
          total_potential_revenue: 0,
          approval_rate: 0,
          staff_list: []
        };
      }
      
      var branchData = monthData.branches[record.branch];
      // メイン商材の架電数を追加
      branchData.total_calls += record.main_product.call_count;
      branchData.total_hours += record.main_product.call_hours;
      branchData.total_appointments += record.main_product.get_appointment;
      
      // サブ商材の架電数も追加
      record.sub_products.forEach(function(subProduct) {
        branchData.total_calls += subProduct.call_count;
        branchData.total_hours += subProduct.call_hours;
        branchData.total_appointments += subProduct.get_appointment;
      });
      
      if (!branchData.staff_list.includes(record.staff)) {
        branchData.staff_list.push(record.staff);
        branchData.staff_count = branchData.staff_list.length;
      }
    }
    
    // 商材別集計
    if (record.main_product.product) {
      if (!monthData.products[record.main_product.product]) {
        monthData.products[record.main_product.product] = {
          product_name: record.main_product.product,
          total_calls: 0,
          total_hours: 0,
          total_appointments: 0,
          total_deals: 0,
          total_approved: 0,
          total_revenue: 0,
          total_potential_revenue: 0,
          approval_rate: 0
        };
      }
      
      var productData = monthData.products[record.main_product.product];
      productData.total_calls += record.main_product.call_count;
      productData.total_hours += record.main_product.call_hours;
      productData.total_appointments += record.main_product.get_appointment;
    }
    
    // サブ商材別集計
    record.sub_products.forEach(function(subProduct) {
      if (subProduct.product) {
        if (!monthData.products[subProduct.product]) {
          monthData.products[subProduct.product] = {
            product_name: subProduct.product,
            total_calls: 0,
            total_hours: 0,
            total_appointments: 0,
            total_deals: 0,
            total_approved: 0,
            total_rejected: 0,
            total_revenue: 0,
            total_potential_revenue: 0,
            approval_rate: 0
          };
        }
        
        var subProductData = monthData.products[subProduct.product];
        subProductData.total_calls += subProduct.call_count;
        subProductData.total_hours += subProduct.call_hours;
        subProductData.total_appointments += subProduct.get_appointment;
      }
    });
    
    // 個人別集計
    if (!monthData.staff[record.staff]) {
      monthData.staff[record.staff] = {
        staff_name: record.staff,
        branch: record.branch,
        join_date: record.join_date,
        total_calls: 0,
        total_hours: 0,
        total_appointments: 0,
        total_deals: 0,
        total_approved: 0,
        total_rejected: 0,
        total_revenue: 0,
        total_potential_revenue: 0,
        approval_rate: 0,
        daily_activity: []
      };
    }
    
    var staffData = monthData.staff[record.staff];
    // メイン商材の架電数を追加
    staffData.total_calls += record.main_product.call_count;
    staffData.total_hours += record.main_product.call_hours;
    staffData.total_appointments += record.main_product.get_appointment;
    
    // サブ商材の架電数も追加
    record.sub_products.forEach(function(subProduct) {
      staffData.total_calls += subProduct.call_count;
      staffData.total_hours += subProduct.call_hours;
      staffData.total_appointments += subProduct.get_appointment;
    });
    
    // 日次活動データ
    staffData.daily_activity.push({
      date: record.date,
      main_product: record.main_product,
      sub_products: record.sub_products
    });
    
    // 全体サマリー
    // メイン商材の架電数を追加
    monthData.summary.total_calls += record.main_product.call_count;
    monthData.summary.total_hours += record.main_product.call_hours;
    monthData.summary.total_appointments += record.main_product.get_appointment;
    
    // サブ商材の架電数も追加
    record.sub_products.forEach(function(subProduct) {
      monthData.summary.total_calls += subProduct.call_count;
      monthData.summary.total_hours += subProduct.call_hours;
      monthData.summary.total_appointments += subProduct.get_appointment;
    });
  });
  
  // 7) 商談・却下データの集計
  deals.forEach(function(deal) {
    if (!deal.date) return;
    
    var month = getMonthFromDate(deal.date);
    if (!monthlyData[month]) return;
    
    var monthData = monthlyData[month];
    
    // 商談ステータスに基づく判定
    var dealStatus = deal.deal_status || '未設定';
    var isApproved = dealStatus === '承認';
    var isRejected = dealStatus === '却下';
    var isPending = dealStatus === '承認待ち' || dealStatus === '要対応';
    
    // 報酬の取得（数値に変換）
    var commission = safeNumber(deal.commission) || 0;
    
    // 全体サマリー
    monthData.summary.total_deals++;
    if (isApproved) {
      monthData.summary.total_approved++;
      monthData.summary.total_revenue += commission; // 承認は確定売上
    } else if (isRejected) {
      monthData.summary.total_rejected++;
      // 却下は売上なし
    } else if (isPending) {
      monthData.summary.total_potential_revenue += commission; // 承認待ち・要対応は潜在売上
    }
    
    // 支部別集計
    if (deal.staff && staffMap[deal.staff] && staffMap[deal.staff].branch) {
      var branch = staffMap[deal.staff].branch;
      if (monthData.branches[branch]) {
        monthData.branches[branch].total_deals++;
        if (isApproved) {
          monthData.branches[branch].total_approved++;
          monthData.branches[branch].total_revenue += commission;
        } else if (isRejected) {
          monthData.branches[branch].total_rejected++;
        } else if (isPending) {
          monthData.branches[branch].total_potential_revenue += commission;
        }
      }
    } else {
      // 支部未設定の場合、「未設定」支部に集計
      if (!monthData.branches['未設定']) {
        monthData.branches['未設定'] = {
          branch_name: '未設定',
          staff_count: 0,
          total_calls: 0,
          total_hours: 0,
          total_appointments: 0,
          total_deals: 0,
          total_approved: 0,
          total_rejected: 0,
          total_revenue: 0,
          total_potential_revenue: 0,
          approval_rate: 0,
          staff_list: []
        };
      }
      monthData.branches['未設定'].total_deals++;
      if (isApproved) {
        monthData.branches['未設定'].total_approved++;
        monthData.branches['未設定'].total_revenue += commission;
      } else if (isRejected) {
        monthData.branches['未設定'].total_rejected++;
      } else if (isPending) {
        monthData.branches['未設定'].total_potential_revenue += commission;
      }
    }
    
      // 商材別集計（TAAANデータから）
    if (deal.product) {
      // TAAANデータの商材情報を優先して使用
      if (!monthData.products[deal.product]) {
        monthData.products[deal.product] = {
          product_name: deal.product,
          total_calls: 0,
          total_hours: 0,
          total_appointments: 0,
          total_deals: 0,
          total_approved: 0,
          total_rejected: 0,
          total_revenue: 0,
          total_potential_revenue: 0,
          approval_rate: 0
        };
      }
      
      monthData.products[deal.product].total_deals++;
      if (isApproved) {
        monthData.products[deal.product].total_approved++;
        monthData.products[deal.product].total_revenue += commission;
      } else if (isRejected) {
        monthData.products[deal.product].total_rejected++;
      } else if (isPending) {
        monthData.products[deal.product].total_potential_revenue += commission;
      }
    } else {
      // 商材未設定の場合、「未設定」商材に集計
      if (!monthData.products['未設定']) {
        monthData.products['未設定'] = {
          product_name: '未設定',
          total_calls: 0,
          total_hours: 0,
          total_appointments: 0,
          total_deals: 0,
          total_approved: 0,
          total_rejected: 0,
          total_revenue: 0,
          total_potential_revenue: 0,
          approval_rate: 0
        };
      }
      monthData.products['未設定'].total_deals++;
      if (isApproved) {
        monthData.products['未設定'].total_approved++;
        monthData.products['未設定'].total_revenue += commission;
      } else if (isRejected) {
        monthData.products['未設定'].total_rejected++;
      } else if (isPending) {
        monthData.products['未設定'].total_potential_revenue += commission;
      }
    }
    
    // 個人別集計
    if (deal.staff && monthData.staff[deal.staff]) {
      monthData.staff[deal.staff].total_deals++;
      if (isApproved) {
        monthData.staff[deal.staff].total_approved++;
        monthData.staff[deal.staff].total_revenue += commission;
      } else if (isRejected) {
        monthData.staff[deal.staff].total_rejected++;
      } else if (isPending) {
        monthData.staff[deal.staff].total_potential_revenue += commission;
      }
    } else {
      // スタッフ未設定の場合、「未設定」スタッフに集計
      if (!monthData.staff['未設定']) {
        monthData.staff['未設定'] = {
          staff_name: '未設定',
          branch: '未設定',
          join_date: null,
          total_calls: 0,
          total_hours: 0,
          total_appointments: 0,
          total_deals: 0,
          total_approved: 0,
          total_rejected: 0,
          total_revenue: 0,
          total_potential_revenue: 0,
          approval_rate: 0,
          daily_activity: []
        };
      }
      monthData.staff['未設定'].total_deals++;
      if (isApproved) {
        monthData.staff['未設定'].total_approved++;
        monthData.staff['未設定'].total_revenue += commission;
      } else if (isRejected) {
        monthData.staff['未設定'].total_rejected++;
      } else if (isPending) {
        monthData.staff['未設定'].total_potential_revenue += commission;
      }
    }
  });
  
  // 8) 承認率の計算
  Object.keys(monthlyData).forEach(function(month) {
    var monthData = monthlyData[month];
    
    // 全体承認率
    if (monthData.summary.total_deals > 0) {
      monthData.summary.approval_rate = (monthData.summary.total_approved / monthData.summary.total_deals * 100).toFixed(2);
    }
    
    // 支部別承認率
    Object.keys(monthData.branches).forEach(function(branch) {
      var branchData = monthData.branches[branch];
      if (branchData.total_deals > 0) {
        branchData.approval_rate = (branchData.total_approved / branchData.total_deals * 100).toFixed(2);
      }
    });
    
    // 商材別承認率
    Object.keys(monthData.products).forEach(function(product) {
      var productData = monthData.products[product];
      if (productData.total_deals > 0) {
        productData.approval_rate = (productData.total_approved / productData.total_deals * 100).toFixed(2);
      }
    });
    
    // 個人別承認率
    Object.keys(monthData.staff).forEach(function(staff) {
      var staffData = monthData.staff[staff];
      if (staffData.total_deals > 0) {
        staffData.approval_rate = (staffData.total_approved / staffData.total_deals * 100).toFixed(2);
      }
    });
  });
  
  // 9) 最終的な分析JSON構造の作成
  var analysisJson = {
    metadata: {
      generated_at: new Date().toISOString(),
      data_period: {
        start_month: Object.keys(monthlyData).sort()[0],
        end_month: Object.keys(monthlyData).sort().pop()
      },
      total_months: Object.keys(monthlyData).length
    },
    monthly_analysis: monthlyData,
    summary_by_period: {
      total_calls: 0,
      total_hours: 0,
      total_appointments: 0,
      total_deals: 0,
      total_approved: 0,
      total_rejected: 0,
      total_revenue: 0,
      total_potential_revenue: 0,
      overall_approval_rate: 0
    }
  };
  
  // 期間全体のサマリー計算
  Object.keys(monthlyData).forEach(function(month) {
    var monthData = monthlyData[month];
    analysisJson.summary_by_period.total_calls += monthData.summary.total_calls;
    analysisJson.summary_by_period.total_hours += monthData.summary.total_hours;
    analysisJson.summary_by_period.total_appointments += monthData.summary.total_appointments;
    analysisJson.summary_by_period.total_deals += monthData.summary.total_deals;
    analysisJson.summary_by_period.total_approved += monthData.summary.total_approved;
    analysisJson.summary_by_period.total_rejected += monthData.summary.total_rejected;
    analysisJson.summary_by_period.total_revenue += monthData.summary.total_revenue;
    analysisJson.summary_by_period.total_potential_revenue += monthData.summary.total_potential_revenue;
  });
  
  if (analysisJson.summary_by_period.total_deals > 0) {
    analysisJson.summary_by_period.overall_approval_rate = 
      (analysisJson.summary_by_period.total_approved / analysisJson.summary_by_period.total_deals * 100).toFixed(2);
  }
  
  // --- 追加: アポ獲得・TAAAN入力・承認の月次/スタッフ別/支部別/商材別集計 ---
  var monthly_conversion = {};

  // 1. 日報アポ獲得集計
  daily.forEach(function(record) {
    var month = record.month;
    if (!month) return;
    if (!monthly_conversion[month]) {
      monthly_conversion[month] = {
        total: {self_reported_appointments: 0, taaan_entries: 0, approved_deals: 0},
        by_staff: {},
        by_branch: {},
        by_product: {}
      };
    }
    // メイン商材
    var mainApp = record.main_product.get_appointment || 0;
    var staff = record.staff || '未設定';
    var branch = record.branch || '未設定';
    var product = record.main_product.product || '未設定';
    // サブ商材
    var subApps = 0;
    record.sub_products.forEach(function(sub) {
      subApps += sub.get_appointment || 0;
    });
    var totalApp = mainApp + subApps;
    // 合計
    monthly_conversion[month].total.self_reported_appointments += totalApp;
    // スタッフ別
    if (!monthly_conversion[month].by_staff[staff]) monthly_conversion[month].by_staff[staff] = {self_reported_appointments: 0, taaan_entries: 0, approved_deals: 0};
    monthly_conversion[month].by_staff[staff].self_reported_appointments += totalApp;
    // 支部別
    if (!monthly_conversion[month].by_branch[branch]) monthly_conversion[month].by_branch[branch] = {self_reported_appointments: 0, taaan_entries: 0, approved_deals: 0};
    monthly_conversion[month].by_branch[branch].self_reported_appointments += totalApp;
    // 商材別
    if (!monthly_conversion[month].by_product[product]) monthly_conversion[month].by_product[product] = {self_reported_appointments: 0, taaan_entries: 0, approved_deals: 0};
    monthly_conversion[month].by_product[product].self_reported_appointments += totalApp;
  });

  // 2. TAAAN入力・承認集計
  deals.forEach(function(deal) {
    var month = getMonthFromDate(deal.date);
    if (!month || !monthly_conversion[month]) return;
    var staff = deal.staff || '未設定';
    var branch = (staffMap[deal.staff] && staffMap[deal.staff].branch) ? staffMap[deal.staff].branch : '未設定';
    var product = deal.product || '未設定';
    
    // TAAAN入力
    monthly_conversion[month].total.taaan_entries++;
    if (!monthly_conversion[month].by_staff[staff]) monthly_conversion[month].by_staff[staff] = {self_reported_appointments: 0, taaan_entries: 0, approved_deals: 0};
    monthly_conversion[month].by_staff[staff].taaan_entries++;
    if (!monthly_conversion[month].by_branch[branch]) monthly_conversion[month].by_branch[branch] = {self_reported_appointments: 0, taaan_entries: 0, approved_deals: 0};
    monthly_conversion[month].by_branch[branch].taaan_entries++;
    if (!monthly_conversion[month].by_product[product]) monthly_conversion[month].by_product[product] = {self_reported_appointments: 0, taaan_entries: 0, approved_deals: 0};
    monthly_conversion[month].by_product[product].taaan_entries++;
    
    // 承認
    if (deal.deal_status === '承認') {
      monthly_conversion[month].total.approved_deals++;
      monthly_conversion[month].by_staff[staff].approved_deals++;
      monthly_conversion[month].by_branch[branch].approved_deals++;
      monthly_conversion[month].by_product[product].approved_deals++;
    }
  });

  // 3. 割合計算
  Object.keys(monthly_conversion).forEach(function(month) {
    var m = monthly_conversion[month];
    // total
    m.total.taaan_rate = m.total.self_reported_appointments > 0 ? m.total.taaan_entries / m.total.self_reported_appointments : null;
    m.total.approval_rate = m.total.taaan_entries > 0 ? m.total.approved_deals / m.total.taaan_entries : null;
    m.total.true_approval_rate = m.total.self_reported_appointments > 0 ? m.total.approved_deals / m.total.self_reported_appointments : null;
    // by_staff
    Object.keys(m.by_staff).forEach(function(staff) {
      var s = m.by_staff[staff];
      s.taaan_rate = s.self_reported_appointments > 0 ? s.taaan_entries / s.self_reported_appointments : null;
      s.approval_rate = s.taaan_entries > 0 ? s.approved_deals / s.taaan_entries : null;
      s.true_approval_rate = s.self_reported_appointments > 0 ? s.approved_deals / s.self_reported_appointments : null;
    });
    // by_branch
    Object.keys(m.by_branch).forEach(function(branch) {
      var b = m.by_branch[branch];
      b.taaan_rate = b.self_reported_appointments > 0 ? b.taaan_entries / b.self_reported_appointments : null;
      b.approval_rate = b.taaan_entries > 0 ? b.approved_deals / b.taaan_entries : null;
      b.true_approval_rate = b.self_reported_appointments > 0 ? b.approved_deals / b.self_reported_appointments : null;
    });
    // by_product
    Object.keys(m.by_product).forEach(function(product) {
      var p = m.by_product[product];
      p.taaan_rate = p.self_reported_appointments > 0 ? p.taaan_entries / p.self_reported_appointments : null;
      p.approval_rate = p.taaan_entries > 0 ? p.approved_deals / p.taaan_entries : null;
      p.true_approval_rate = p.self_reported_appointments > 0 ? p.approved_deals / p.self_reported_appointments : null;
    });
  });

  // 4. analysisJsonに追加
  analysisJson.monthly_conversion = monthly_conversion;
  
  // 10) JSON出力
  var json = JSON.stringify(analysisJson, null, 2);
  var file = saveFileToAllPeriodDirectory('sales_analysis_data.json', json);
  Logger.log('✅ 分析用JSON出力完了: ' + file.getUrl());
  
  return analysisJson;
}

// 詳細分析JSON生成関数を修正
function generateDetailedAnalysisJson(reportPeriod) {
  // 基本的な分析JSONを取得
  var basicAnalysis = generateAnalysisJson();
  // 詳細分析データを追加
  var detailedAnalysis = {
    ...basicAnalysis,
    detailed_metrics: {
      acquisition_analysis: {
        new_customers: {},
        existing_customers: {},
        acquisition_efficiency: {}
      },
      activity_efficiency: {
        calls_per_hour: {},
        appointments_per_call: {},
        deals_per_appointment: {},
        revenue_per_deal: {}
      },
      trend_analysis: {
        monthly_trends: {},
        branch_comparison: {},
        product_performance: {}
      }
    }
  };
  // ...（中略：詳細分析の計算処理はそのまま）...
  // 詳細分析JSON出力
  var json = JSON.stringify(detailedAnalysis, null, 2);
  var fileName = 'detailed_sales_analysis_' + reportPeriod + '.json';
  var file = saveFileToTargetDirectory(fileName, json);
  Logger.log('✅ 詳細分析用JSON出力完了: ' + file.getUrl());
  return detailedAnalysis;
}

// 月次定例報告用の統合関数を修正
function generateMonthlyReport(reportPeriod) {
  Logger.log('📊 月次定例報告生成開始: ' + reportPeriod);
  // 1) 分析用JSON生成
  var analysisData = generateAnalysisJson();
  // 2) 詳細分析JSON生成（reportPeriodを渡す）
  var detailedData = generateDetailedAnalysisJson(reportPeriod);
  // 3) 定着率分析JSON生成
  var retentionData = generateRetentionAnalysisJson();
  // 4) 月次サマリーJSON生成
  var monthlySummary = generateMonthlySummary(analysisData, detailedData, retentionData, reportPeriod);
  // 5) フォルダ作成・ファイル保存
  saveMonthlyReports(reportPeriod, analysisData, detailedData, retentionData, monthlySummary);
  Logger.log('✅ 月次定例報告生成完了: ' + reportPeriod);
  return {
    period: reportPeriod,
    files_created: 4,
    summary: monthlySummary
  };
}

// 月次レポート保存関数を修正
function saveMonthlyReports(reportPeriod, analysisData, detailedData, retentionData, monthlySummary) {
  try {
    // 1) 特定ディレクトリまたは月次レポート用フォルダを取得
    var folder = getTargetDirectory();
    var folderName = getConfig('file_management.folder_name') || "月次営業分析レポート";
    var fileNaming = getConfig('file_management.file_naming') || {};
    
    // 特定ディレクトリが設定されていない場合は従来の方法でフォルダを取得
    if (!folder) {
      var folders = DriveApp.getFoldersByName(folderName);
      if (folders.hasNext()) {
        folder = folders.next();
      } else {
        folder = DriveApp.createFolder(folderName);
        Logger.log('📁 フォルダ作成: ' + folderName);
      }
    }
    // 2) 各JSONファイルを保存
    var files = [];
    // 月次サマリー
    if (monthlySummary) {
      var summaryJson = JSON.stringify(monthlySummary, null, 2);
      var summaryFileName = (fileNaming.summary || "月次サマリー_") + reportPeriod + '.json';
      var summaryBlob = Utilities.newBlob(summaryJson, 'application/json', summaryFileName);
      var summaryFile = folder.createFile(summaryBlob);
      files.push(summaryFile.getName());
      Logger.log('📄 月次サマリー保存: ' + summaryFile.getName());
    }
    // 定着率分析
    var retentionJson = JSON.stringify(retentionData, null, 2);
    var retentionFileName = (fileNaming.retention || "定着率分析_") + reportPeriod + '.json';
    var retentionBlob = Utilities.newBlob(retentionJson, 'application/json', retentionFileName);
    var retentionFile = folder.createFile(retentionBlob);
    files.push(retentionFile.getName());
    Logger.log('📄 定着率分析保存: ' + retentionFile.getName());
    // 詳細分析
    var detailedJson = JSON.stringify(detailedData, null, 2);
    var detailedFileName = (fileNaming.detailed || "詳細分析_") + reportPeriod + '.json';
    var detailedBlob = Utilities.newBlob(detailedJson, 'application/json', detailedFileName);
    var detailedFile = folder.createFile(detailedBlob);
    files.push(detailedFile.getName());
    Logger.log('📄 詳細分析保存: ' + detailedFile.getName());
    // 基本分析
    var analysisJson = JSON.stringify(analysisData, null, 2);
    var analysisFileName = (fileNaming.basic || "基本分析_") + reportPeriod + '.json';
    var analysisBlob = Utilities.newBlob(analysisJson, 'application/json', analysisFileName);
    var analysisFile = folder.createFile(analysisBlob);
    files.push(analysisFile.getName());
    Logger.log('📄 基本分析保存: ' + analysisFile.getName());
    // 3) 実行ログファイルを作成
    var logData = {
      execution_time: new Date().toISOString(),
      report_period: reportPeriod,
      files_created: files,
      folder_url: folder.getUrl(),
      config_version: getConfig('metadata.version') || '1.0',
      summary: {
        total_staff: Object.keys(retentionData.staff_retention_analysis).length,
        total_calls: analysisData.summary_by_period.total_calls,
        total_deals: analysisData.summary_by_period.total_deals,
        approval_rate: analysisData.summary_by_period.overall_approval_rate
      }
    };
    var logJson = JSON.stringify(logData, null, 2);
    var logFileName = (fileNaming.log || "実行ログ_") + reportPeriod + '.json';
    var logBlob = Utilities.newBlob(logJson, 'application/json', logFileName);
    var logFile = folder.createFile(logBlob);
    Logger.log('✅ 月次レポート保存完了');
    Logger.log('📁 フォルダURL: ' + folder.getUrl());
    Logger.log('📄 作成ファイル数: ' + files.length);
    return {
      folder: folder,
      files: files,
      log: logFile
    };
  } catch (error) {
    Logger.log('❌ ファイル保存エラー: ' + error.message);
    throw error;
  }
}

// 月次定例報告を全月分生成する関数（効率化版）
function generateMonthlyReportForAllMonths() {
  Logger.log('📊 全月分の月次レポート生成開始（効率化版）');
  
  // 1) スプレッドシートから全ての月を抽出
  var ss = SpreadsheetApp.openById('1tZDpkzCCYTgeq1NqSFHr9HB-1J3VUMw3vncKCrhUOqU');
  var dailySheet = ss.getSheetByName('学生日報');
  var lastCol = dailySheet.getLastColumn();
  var dailyRaw = dailySheet.getRange(3,1, dailySheet.getLastRow()-2, lastCol).getValues();
  
  // 日付列のインデックスを特定
  var groupRow = dailySheet.getRange(1,1,1,lastCol).getValues()[0];
  var columnRow = dailySheet.getRange(2,1,1,lastCol).getValues()[0];
  var dailyHeaders = [];
  var currentGroup = '';
  for (var i = 0; i < lastCol; i++) {
    var group = groupRow[i] || currentGroup;
    var column = columnRow[i];
    if (group && group !== currentGroup) currentGroup = group;
    if (column) {
      var headerName = currentGroup ? currentGroup + '_' + column : column;
      dailyHeaders.push(headerName);
    } else {
      dailyHeaders.push('');
    }
  }
  var dateColIdx = dailyHeaders.indexOf('今日の日付');
  if (dateColIdx === -1) throw new Error('日付列が見つかりません');
  
  // 全ての月を抽出
  var monthsSet = {};
  dailyRaw.forEach(function(row) {
    var dateStr = row[dateColIdx];
    if (!dateStr) return;
    var date = new Date(dateStr);
    if (isNaN(date.getTime())) return;
    var month = date.getFullYear() + '-' + ('0' + (date.getMonth() + 1)).slice(-2);
    monthsSet[month] = true;
  });
  var months = Object.keys(monthsSet).sort();
  
  Logger.log('📅 対象月: ' + months.join(', '));
  
  // 2) 全月データを1回だけ生成（重複防止）
  Logger.log('📊 全月データ生成開始...');
  var analysisData = generateAnalysisJson();      // 基本分析（全月）
  var retentionData = generateRetentionAnalysisJson();  // 定着率分析（全月）
  mergeSalesDataNested();  // 統合データ（全月）
  Logger.log('✅ 全月データ生成完了');
  
  // 3) 各月ごとに月次特化データのみを生成
  Logger.log('📊 月次レポート生成開始...');
  var monthlyResults = [];
  
  months.forEach(function(month) {
    Logger.log('📅 月次レポート生成中: ' + month);
    
    // 既存の月次ファイルを削除
    try {
      var targetFolder = getTargetDirectory();
      var folder = null;
      
      if (targetFolder) {
        folder = targetFolder;
      } else {
        var folderName = getConfig('file_management.folder_name') || "月次営業分析レポート";
        var folders = DriveApp.getFoldersByName(folderName);
        if (folders.hasNext()) {
          folder = folders.next();
        } else {
          folder = DriveApp.createFolder(folderName);
        }
      }
      
      if (folder) {
        var files = folder.getFiles();
        while (files.hasNext()) {
          var file = files.next();
          var fileName = file.getName();
                     // 月次ファイルのみ削除（全月データファイルは保護）
           if (fileName.includes(month) && 
               !fileName.includes('sales_analysis_data.json') && 
               !fileName.includes('staff_retention_analysis.json') && 
               !fileName.includes('merged_sales_data.json')) {
             file.setTrashed(true);
             Logger.log('🗑️ 既存月次ファイル削除: ' + fileName);
           }
        }
      }
    } catch (error) {
      Logger.log('⚠️ 既存ファイル削除エラー: ' + error.message);
    }
    
    // 月次特化データのみ生成
    var detailedData = generateDetailedAnalysisJson(month);  // 詳細分析（月次）
    var monthlySummary = generateMonthlySummary(analysisData, detailedData, retentionData, month);  // 月次サマリー
    
    // 月次ファイルのみ保存（全月データは除外）
    saveMonthlyReportsOptimized(month, analysisData, detailedData, retentionData, monthlySummary);
    
    monthlyResults.push({
      month: month,
      files_created: 4
    });
  });
  
  Logger.log('✅ 全月分の月次レポート生成完了');
  Logger.log('📊 処理結果:');
  Logger.log('  - 全月データファイル: 3個（重複なし）');
  Logger.log('  - 月次レポートファイル: ' + (months.length * 4) + '個（' + months.length + '月 × 4ファイル）');
  Logger.log('  - 対象月: ' + months.join(', '));
  
  return {
    months_processed: months.length,
    total_files: 3 + (months.length * 4),
    monthly_results: monthlyResults
  };
}

function generateRetentionAnalysisJson() {
  // ヘルパー関数: 安全な日時変換
  function safeDateConversion(dateValue) {
    if (!dateValue) return null;
    
    try {
      if (typeof dateValue === 'string') {
        if (dateValue.trim() === '') return null;
        
        var dateStr = dateValue.toString().trim();
        
        if (/^\d{4}\/\d{1,2}\/\d{1,2}$/.test(dateStr)) {
          return new Date(dateStr).toISOString();
        }
        
        if (/^\d{4}\/\d{1,2}\/\d{1,2}\s+\d{1,2}:\d{1,2}:\d{1,2}$/.test(dateStr)) {
          return new Date(dateStr).toISOString();
        }
        
        var date = new Date(dateStr);
        if (isNaN(date.getTime())) return null;
        return date.toISOString();
      }
      
      if (dateValue instanceof Date) {
        if (isNaN(dateValue.getTime())) return null;
        return dateValue.toISOString();
      }
      
      return null;
    } catch (e) {
      Logger.log('日時変換エラー: ' + dateValue + ' - ' + e.message);
      return null;
    }
  }

  // ヘルパー関数: 月次データの取得
  function getMonthFromDate(dateStr) {
    if (!dateStr) return null;
    return dateStr.substring(0, 7); // YYYY-MM形式
  }

  // ヘルパー関数: 数値変換
  function safeNumber(value) {
    if (value === null || value === undefined || value === '') return 0;
    var num = parseFloat(value);
    return isNaN(num) ? 0 : num;
  }

  // ヘルパー関数: 日付の差分計算（月数）
  function getMonthsBetween(date1, date2) {
    if (!date1 || !date2) return 0;
    var d1 = new Date(date1);
    var d2 = new Date(date2);
    return (d2.getFullYear() - d1.getFullYear()) * 12 + (d2.getMonth() - d1.getMonth());
  }

  // 1) スプレッドシートを開く
  var SPREADSHEET_ID = '1tZDpkzCCYTgeq1NqSFHr9HB-1J3VUMw3vncKCrhUOqU';
  var ss = SpreadsheetApp.openById(SPREADSHEET_ID);

  // 2) スタッフ一覧読み込み
  var staffSheet = ss.getSheetByName('スタッフ一覧');
  var staffData = staffSheet.getDataRange().getValues();
  var staffMap = {};
  staffData.forEach(function(row, i) {
    if (i === 0) return; // ヘッダー行をスキップ
    var name = row[1];           // 列B: スタッフ名
    var joinDate = safeDateConversion(row[2]); // 列C: 入社日
    var branch = row[3];         // 列D: 支部
    staffMap[name] = {
      join_date: joinDate,
      branch: branch
    };
  });

  // 3) 日報読み込み
  var dailySheet = ss.getSheetByName('学生日報');
  var lastCol = dailySheet.getLastColumn();
  
  var groupRow = dailySheet.getRange(1,1,1,lastCol).getValues()[0];
  var columnRow = dailySheet.getRange(2,1,1,lastCol).getValues()[0];
  
  var dailyHeaders = [];
  var currentGroup = '';
  
  for (var i = 0; i < lastCol; i++) {
    var group = groupRow[i] || currentGroup;
    var column = columnRow[i];
    
    if (group && group !== currentGroup) {
      currentGroup = group;
    }
    
    if (column) {
      var headerName = currentGroup ? currentGroup + '_' + column : column;
      dailyHeaders.push(headerName);
    } else {
      dailyHeaders.push('');
    }
  }
  
  var dailyRaw = dailySheet.getRange(3,1, dailySheet.getLastRow()-2, lastCol).getValues();
  var daily = dailyRaw.map(function(row, idx) {
    var rec = {};
    dailyHeaders.forEach(function(h,i){ 
      if (h) rec[h] = row[i]; 
    });
    
    // メイン商材のデータを取得
    var mainProduct = rec['メイン商材_新規架電：メイン商材'] || rec['新規架電：メイン商材'];
    var mainCallHours = safeNumber(rec['メイン商材_総荷電時間(単位は●時間)'] || rec['総荷電時間(単位は●時間)']);
    var mainCallCount = safeNumber(rec['メイン商材_架電数　※半角で入力'] || rec['架電数　※半角で入力']);
    var mainReceptionBk = safeNumber(rec['メイン商材_受付BK　※半角で入力'] || rec['受付BK　※半角で入力']);
    var mainNoOneInCharge = safeNumber(rec['メイン商材_担当不在　※半角で入力'] || rec['担当不在　※半角で入力']);
    var mainDisconnect = safeNumber(rec['メイン商材_不通　※半角で入力'] || rec['不通　※半角で入力']);
    var mainChargeConnected = safeNumber(rec['メイン商材_担当コネクト　※半角で入力'] || rec['担当コネクト　※半角で入力']);
    var mainChargeBk = safeNumber(rec['メイン商材_担当BK（見込みも含む）　※半角で入力'] || rec['担当BK（見込みも含む）　※半角で入力']);
    var mainGetAppointment = safeNumber(rec['メイン商材_アポ獲得　※半角で入力'] || rec['アポ獲得　※半角で入力']);
    
    return {
      date: safeDateConversion(rec['今日の日付']),
      month: getMonthFromDate(safeDateConversion(rec['今日の日付'])),
      staff: rec['名前'],
      branch: staffMap[rec['名前']] ? staffMap[rec['名前']].branch : null,
      join_date: staffMap[rec['名前']] ? staffMap[rec['名前']].join_date : null,
      main_product: {
        product: mainProduct,
        call_hours: mainCallHours,
        call_count: mainCallCount,
        reception_bk: mainReceptionBk,
        no_one_in_charge: mainNoOneInCharge,
        disconnect: mainDisconnect,
        charge_connected: mainChargeConnected,
        charge_bk: mainChargeBk,
        get_appointment: mainGetAppointment
      },
      sub_products: []
    };
  });

  // 4) 学生別の活動履歴を作成
  var staffActivityHistory = {};
  var allMonths = new Set();
  
  daily.forEach(function(record) {
    if (!record.staff || !record.date) return;
    
    if (!staffActivityHistory[record.staff]) {
      staffActivityHistory[record.staff] = {
        staff_name: record.staff,
        branch: record.branch,
        join_date: record.join_date,
        activity_months: {},
        first_activity_date: record.date,
        last_activity_date: record.date,
        total_activity_days: 0,
        total_calls: 0,
        total_hours: 0,
        total_appointments: 0
      };
    }
    
    var staffData = staffActivityHistory[record.staff];
    var month = record.month;
    
    if (!staffData.activity_months[month]) {
      staffData.activity_months[month] = {
        month: month,
        activity_days: 0,
        total_calls: 0,
        total_hours: 0,
        total_appointments: 0,
        daily_activities: []
      };
    }
    
    // 月次データを更新
    var monthData = staffData.activity_months[month];
    monthData.activity_days++;
    monthData.total_calls += record.call_count;
    monthData.total_hours += record.call_hours;
    monthData.total_appointments += record.get_appointment;
    monthData.daily_activities.push({
      date: record.date,
      call_count: record.call_count,
      call_hours: record.call_hours,
      get_appointment: record.get_appointment,
      product: record.main_product.product
    });
    
    // 全体データを更新
    staffData.total_activity_days++;
    staffData.total_calls += record.call_count;
    staffData.total_hours += record.call_hours;
    staffData.total_appointments += record.get_appointment;
    staffData.last_activity_date = record.date;
    
    allMonths.add(month);
  });
  
  // 5) 定着率・離脱リスク分析
  var retentionAnalysis = {
    metadata: {
      generated_at: new Date().toISOString(),
      analysis_period: {
        start_month: Array.from(allMonths).sort()[0],
        end_month: Array.from(allMonths).sort().pop()
      },
      total_months: allMonths.size
    },
    staff_retention_analysis: {},
    monthly_retention_rates: {},
    branch_retention_analysis: {},
    risk_analysis: {
      high_risk_staff: [],
      medium_risk_staff: [],
      low_risk_staff: []
    }
  };
  
  // 学生別の定着分析
  Object.keys(staffActivityHistory).forEach(function(staffName) {
    var staffData = staffActivityHistory[staffName];
    var joinDate = staffData.join_date;
    var lastActivityDate = staffData.last_activity_date;
    var firstActivityDate = staffData.first_activity_date;
    
    // 在籍期間の計算
    var monthsSinceJoin = joinDate ? getMonthsBetween(joinDate, lastActivityDate) : 0;
    var monthsSinceFirstActivity = getMonthsBetween(firstActivityDate, lastActivityDate);
    
    // 活動月数の計算
    var activeMonths = Object.keys(staffData.activity_months).length;
    
    // 月次活動率の計算
    var monthlyActivityRate = allMonths.size > 0 ? (activeMonths / allMonths.size * 100).toFixed(2) : 0;
    
    // 平均月次活動日数
    var avgMonthlyActivityDays = activeMonths > 0 ? (staffData.total_activity_days / activeMonths).toFixed(2) : 0;
    
    // 離脱リスクスコアの計算
    var riskScore = 0;
    var riskFactors = [];
    
    // 設定ファイルから閾値を取得
    var weights = getConfig('risk_scoring.weights') || {};
    var factors = getConfig('risk_scoring.factors') || {};
    
    // リスク要因1: 活動率が低い
    var activityRateThreshold = factors.activity_rate_threshold || 50;
    if (monthlyActivityRate < activityRateThreshold) {
      riskScore += weights.low_activity_rate || 30;
      riskFactors.push("活動率が" + activityRateThreshold + "%未満");
    }
    
    // リスク要因2: 最近の活動が少ない
    var recentActivityDaysThreshold = factors.recent_activity_days_threshold || 5;
    var recentMonths = Object.keys(staffData.activity_months).sort().slice(-3);
    var recentActivityDays = 0;
    recentMonths.forEach(function(month) {
      recentActivityDays += staffData.activity_months[month].activity_days;
    });
    if (recentActivityDays < recentActivityDaysThreshold) {
      riskScore += weights.recent_inactivity || 25;
      riskFactors.push("最近3ヶ月の活動日数が" + recentActivityDaysThreshold + "日未満");
    }
    
    // リスク要因3: 成果が低い
    var appointmentRateThreshold = factors.appointment_rate_threshold || 2;
    var appointmentRate = staffData.total_calls > 0 ? (staffData.total_appointments / staffData.total_calls * 100) : 0;
    if (appointmentRate < appointmentRateThreshold) {
      riskScore += weights.low_performance || 20;
      riskFactors.push("アポ獲得率が" + appointmentRateThreshold + "%未満");
    }
    
    // リスク要因4: 在籍期間が短いが活動が少ない
    var shortTenureMonths = factors.short_tenure_months || 3;
    var minActivityDaysShortTenure = factors.min_activity_days_short_tenure || 10;
    if (monthsSinceJoin < shortTenureMonths && staffData.total_activity_days < minActivityDaysShortTenure) {
      riskScore += weights.short_tenure_low_activity || 15;
      riskFactors.push("入社" + shortTenureMonths + "ヶ月未満で活動日数が" + minActivityDaysShortTenure + "日未満");
    }
    
    // リスク要因5: 活動の安定性が低い
    var activityVarianceThreshold = factors.activity_variance_threshold || 10;
    var activityVariance = 0;
    var activityDays = [];
    Object.keys(staffData.activity_months).forEach(function(month) {
      activityDays.push(staffData.activity_months[month].activity_days);
    });
    if (activityDays.length > 1) {
      var avg = activityDays.reduce((a, b) => a + b, 0) / activityDays.length;
      activityVariance = activityDays.reduce((sum, day) => sum + Math.pow(day - avg, 2), 0) / activityDays.length;
    }
    if (activityVariance > activityVarianceThreshold) {
      riskScore += weights.unstable_activity || 10;
      riskFactors.push("活動のばらつきが大きい（閾値: " + activityVarianceThreshold + "）");
    }
    
    // リスクレベル判定（設定ファイルの閾値を使用）
    var thresholds = getConfig('risk_scoring.thresholds') || {};
    var highRiskThreshold = thresholds.high_risk || 50;
    var mediumRiskThreshold = thresholds.medium_risk || 30;
    
    var riskLevel = "low";
    if (riskScore >= highRiskThreshold) {
      riskLevel = "high";
      retentionAnalysis.risk_analysis.high_risk_staff.push(staffName);
    } else if (riskScore >= mediumRiskThreshold) {
      riskLevel = "medium";
      retentionAnalysis.risk_analysis.medium_risk_staff.push(staffName);
    } else {
      retentionAnalysis.risk_analysis.low_risk_staff.push(staffName);
    }
    
    retentionAnalysis.staff_retention_analysis[staffName] = {
      staff_name: staffName,
      branch: staffData.branch,
      join_date: joinDate,
      first_activity_date: firstActivityDate,
      last_activity_date: lastActivityDate,
      months_since_join: monthsSinceJoin,
      months_since_first_activity: monthsSinceFirstActivity,
      active_months: activeMonths,
      total_activity_days: staffData.total_activity_days,
      monthly_activity_rate: monthlyActivityRate,
      avg_monthly_activity_days: avgMonthlyActivityDays,
      total_calls: staffData.total_calls,
      total_hours: staffData.total_hours,
      total_appointments: staffData.total_appointments,
      appointment_rate: appointmentRate.toFixed(2),
      risk_score: riskScore,
      risk_level: riskLevel,
      risk_factors: riskFactors,
      activity_months: staffData.activity_months
    };
  });
  
  // 6) 月次定着率の計算
  var sortedMonths = Array.from(allMonths).sort();
  sortedMonths.forEach(function(month, index) {
    var activeStaffThisMonth = 0;
    var totalStaffThisMonth = 0;
    
    Object.keys(staffActivityHistory).forEach(function(staffName) {
      var staffData = staffActivityHistory[staffName];
      var joinMonth = staffData.join_date ? getMonthFromDate(staffData.join_date) : null;
      
      // その月に在籍していた学生をカウント
      if (!joinMonth || joinMonth <= month) {
        totalStaffThisMonth++;
        if (staffData.activity_months[month]) {
          activeStaffThisMonth++;
        }
      }
    });
    
    retentionAnalysis.monthly_retention_rates[month] = {
      month: month,
      active_staff: activeStaffThisMonth,
      total_staff: totalStaffThisMonth,
      retention_rate: totalStaffThisMonth > 0 ? (activeStaffThisMonth / totalStaffThisMonth * 100).toFixed(2) : 0
    };
  });
  
  // 7) 支部別定着分析
  var branchAnalysis = {};
  Object.keys(staffActivityHistory).forEach(function(staffName) {
    var staffData = staffActivityHistory[staffName];
    var branch = staffData.branch || "未分類";
    
    if (!branchAnalysis[branch]) {
      branchAnalysis[branch] = {
        branch_name: branch,
        total_staff: 0,
        active_staff: 0,
        high_risk_staff: 0,
        medium_risk_staff: 0,
        low_risk_staff: 0,
        avg_activity_rate: 0,
        avg_risk_score: 0
      };
    }
    
    var branchData = branchAnalysis[branch];
    branchData.total_staff++;
    
    var staffRetentionData = retentionAnalysis.staff_retention_analysis[staffName];
    branchData.avg_activity_rate += parseFloat(staffRetentionData.monthly_activity_rate);
    branchData.avg_risk_score += staffRetentionData.risk_score;
    
    if (staffRetentionData.risk_level === "high") {
      branchData.high_risk_staff++;
    } else if (staffRetentionData.risk_level === "medium") {
      branchData.medium_risk_staff++;
    } else {
      branchData.low_risk_staff++;
    }
    
    if (staffRetentionData.monthly_activity_rate > 50) {
      branchData.active_staff++;
    }
  });
  
  // 支部別の平均値を計算
  Object.keys(branchAnalysis).forEach(function(branch) {
    var branchData = branchAnalysis[branch];
    if (branchData.total_staff > 0) {
      branchData.avg_activity_rate = (branchData.avg_activity_rate / branchData.total_staff).toFixed(2);
      branchData.avg_risk_score = (branchData.avg_risk_score / branchData.total_staff).toFixed(2);
    }
  });
  
  retentionAnalysis.branch_retention_analysis = branchAnalysis;
  
  // 8) JSON出力
  var json = JSON.stringify(retentionAnalysis, null, 2);
  var file = saveFileToAllPeriodDirectory('staff_retention_analysis.json', json);
  Logger.log('✅ 定着率分析用JSON出力完了: ' + file.getUrl());
  
  return retentionAnalysis;
}

// 月次サマリー生成関数
function generateMonthlySummary(analysisData, detailedData, retentionData, reportPeriod) {
  var currentMonth = reportPeriod;
  var monthData = analysisData.monthly_analysis[currentMonth];
  
  if (!monthData) {
    Logger.log('⚠️ 指定月のデータが見つかりません: ' + currentMonth);
    return null;
  }
  
  var summary = {
    metadata: {
      report_period: reportPeriod,
      generated_at: new Date().toISOString(),
      report_type: "monthly_summary"
    },
    key_metrics: {
      total_calls: monthData.summary.total_calls,
      total_hours: monthData.summary.total_hours,
      total_appointments: monthData.summary.total_appointments,
      total_deals: monthData.summary.total_deals,
      total_approved: monthData.summary.total_approved,
      total_rejected: monthData.summary.total_rejected,
      approval_rate: monthData.summary.approval_rate
    },
    deal_status_breakdown: {
      approved: monthData.summary.total_approved,
      rejected: monthData.summary.total_rejected,
      pending: monthData.summary.total_deals - monthData.summary.total_approved - monthData.summary.total_rejected,
      total: monthData.summary.total_deals
    },
    branch_performance: {},
    product_performance: {},
    staff_performance: {},
    retention_metrics: {
      total_staff: Object.keys(retentionData.staff_retention_analysis).length,
      active_staff: 0,
      high_risk_staff: retentionData.risk_analysis.high_risk_staff.length,
      medium_risk_staff: retentionData.risk_analysis.medium_risk_staff.length,
      low_risk_staff: retentionData.risk_analysis.low_risk_staff.length,
      retention_rate: retentionData.monthly_retention_rates[currentMonth] ? 
        retentionData.monthly_retention_rates[currentMonth].retention_rate : 0
    },
    alerts: []
  };
  
  // 支部別パフォーマンス
  Object.keys(monthData.branches).forEach(function(branch) {
    var branchData = monthData.branches[branch];
    summary.branch_performance[branch] = {
      total_calls: branchData.total_calls,
      total_hours: branchData.total_hours,
      total_appointments: branchData.total_appointments,
      total_deals: branchData.total_deals,
      total_approved: branchData.total_approved,
      total_revenue: branchData.total_revenue,
      total_potential_revenue: branchData.total_potential_revenue,
      approval_rate: branchData.approval_rate,
      calls_per_staff: branchData.calls_per_staff,
      hours_per_staff: branchData.hours_per_staff
    };
  });
  
  // 商材別パフォーマンス
  Object.keys(monthData.products).forEach(function(product) {
    var productData = monthData.products[product];
    summary.product_performance[product] = {
      // 日報データ（架電関連）
      total_calls: productData.total_calls,
      total_hours: productData.total_hours,
      total_appointments: productData.total_appointments,
      // TAAANデータ（商談関連）
      total_deals: productData.total_deals,
      total_approved: productData.total_approved,
      total_revenue: productData.total_revenue,
      total_potential_revenue: productData.total_potential_revenue,
      approval_rate: productData.approval_rate,
      calls_per_hour: productData.calls_per_hour,
      appointments_per_call: productData.appointments_per_call
    };
  });
  
  // 個人別パフォーマンス（上位N名）
  var topStaffCount = getConfig('monthly_summary.top_staff_count') || 10;
  var staffArray = [];
  Object.keys(monthData.staff).forEach(function(staff) {
    var staffData = monthData.staff[staff];
    staffArray.push({
      staff_name: staff,
      branch: staffData.branch,
      total_calls: staffData.total_calls,
      total_hours: staffData.total_hours,
      total_appointments: staffData.total_appointments,
      total_deals: staffData.total_deals,
      total_approved: staffData.total_approved,
      total_revenue: staffData.total_revenue,
      total_potential_revenue: staffData.total_potential_revenue,
      approval_rate: staffData.approval_rate,
      calls_per_hour: staffData.calls_per_hour
    });
  });
  
  // 架電数でソートして上位N名を取得
  staffArray.sort(function(a, b) {
    return b.total_calls - a.total_calls;
  });
  
  staffArray.slice(0, topStaffCount).forEach(function(staff) {
    summary.staff_performance[staff.staff_name] = staff;
  });
  
  // 定着率メトリクス
  var activityRateThreshold = getConfig('risk_scoring.factors.activity_rate_threshold') || 50;
  summary.retention_metrics.active_staff = Object.keys(retentionData.staff_retention_analysis).filter(function(staff) {
    var staffData = retentionData.staff_retention_analysis[staff];
    return parseFloat(staffData.monthly_activity_rate) > activityRateThreshold;
  }).length;
  
  // アラート生成（設定ファイルの閾値を使用）
  var approvalRateWarning = getConfig('alerts.approval_rate.warning_threshold') || 60;
  var approvalRateCritical = getConfig('alerts.approval_rate.critical_threshold') || 50;
  var highRiskWarning = getConfig('alerts.high_risk_staff.warning_threshold') || 3;
  var highRiskCritical = getConfig('alerts.high_risk_staff.critical_threshold') || 5;
  var retentionWarning = getConfig('alerts.retention.warning_threshold') || 70;
  var retentionCritical = getConfig('alerts.retention.critical_threshold') || 60;
  
  // 承認率アラート
  var approvalRate = parseFloat(summary.key_metrics.approval_rate);
  if (approvalRate < approvalRateCritical) {
    summary.alerts.push({
      type: "critical",
      message: "承認率が危険レベルを下回っています",
      value: summary.key_metrics.approval_rate + "%",
      threshold: approvalRateCritical + "%"
    });
  } else if (approvalRate < approvalRateWarning) {
    summary.alerts.push({
      type: "warning",
      message: "承認率が警告レベルを下回っています",
      value: summary.key_metrics.approval_rate + "%",
      threshold: approvalRateWarning + "%"
    });
  }
  
  // 高リスク学生アラート
  if (summary.retention_metrics.high_risk_staff >= highRiskCritical) {
    summary.alerts.push({
      type: "critical",
      message: "高リスク学生が危険レベルを超えています",
      value: summary.retention_metrics.high_risk_staff + "名",
      threshold: highRiskCritical + "名"
    });
  } else if (summary.retention_metrics.high_risk_staff >= highRiskWarning) {
    summary.alerts.push({
      type: "warning",
      message: "高リスク学生が警告レベルを超えています",
      value: summary.retention_metrics.high_risk_staff + "名",
      threshold: highRiskWarning + "名"
    });
  }
  
  // 定着率アラート
  var retentionRate = parseFloat(summary.retention_metrics.retention_rate);
  if (retentionRate < retentionCritical) {
    summary.alerts.push({
      type: "critical",
      message: "定着率が危険レベルを下回っています",
      value: summary.retention_metrics.retention_rate + "%",
      threshold: retentionCritical + "%"
    });
  } else if (retentionRate < retentionWarning) {
    summary.alerts.push({
      type: "warning",
      message: "定着率が警告レベルを下回っています",
      value: summary.retention_metrics.retention_rate + "%",
      threshold: retentionWarning + "%"
    });
  }
  
  // 支部×商材クロス分析データを生成
  summary.branch_product_cross_analysis = generateBranchProductCrossAnalysis(analysisData, reportPeriod);
  
  return summary;
}

// 支部×商材クロス分析データを生成する関数
function generateBranchProductCrossAnalysis(analysisData, reportPeriod) {
  var crossAnalysis = {
    taaan_deals: {},
    approved_deals: {},
    total_revenue: {}
  };
  
  // 指定月のデータを取得
  var monthData = analysisData.monthly_analysis[reportPeriod];
  if (!monthData) {
    Logger.log('⚠️ 指定月のデータが見つかりません: ' + reportPeriod);
    return crossAnalysis;
  }
  
  // 支部×商材のクロス集計を実行
  Object.keys(monthData.staff).forEach(function(staffName) {
    var staffData = monthData.staff[staffName];
    var branch = staffData.branch || '未設定';
    
    // スタッフのTAAANデータを商材別に配分
    var staffDeals = staffData.total_deals || 0;
    var staffApproved = staffData.total_approved || 0;
    var staffRevenue = staffData.total_revenue || 0;
    
    // 商材別の配分を計算（product_performanceの比率を使用）
    if (staffDeals > 0 && monthData.products) {
      var totalProductDeals = 0;
      var productRatios = {};
      
      // 各商材の商談数を合計
      Object.keys(monthData.products).forEach(function(product) {
        var productDeals = monthData.products[product].total_deals || 0;
        totalProductDeals += productDeals;
        productRatios[product] = productDeals;
      });
      
      // 商材別にデータを配分
      Object.keys(productRatios).forEach(function(product) {
        if (totalProductDeals > 0) {
          var ratio = productRatios[product] / totalProductDeals;
          
          // 支部×商材のキーを作成
          var branchKey = branch;
          var productKey = product;
          
          // TAAAN商談数
          if (!crossAnalysis.taaan_deals[branchKey]) {
            crossAnalysis.taaan_deals[branchKey] = {};
          }
          if (!crossAnalysis.taaan_deals[branchKey][productKey]) {
            crossAnalysis.taaan_deals[branchKey][productKey] = 0;
          }
          crossAnalysis.taaan_deals[branchKey][productKey] += Math.round(staffDeals * ratio);
          
          // 承認数
          if (!crossAnalysis.approved_deals[branchKey]) {
            crossAnalysis.approved_deals[branchKey] = {};
          }
          if (!crossAnalysis.approved_deals[branchKey][productKey]) {
            crossAnalysis.approved_deals[branchKey][productKey] = 0;
          }
          crossAnalysis.approved_deals[branchKey][productKey] += Math.round(staffApproved * ratio);
          
          // 確定売上
          if (!crossAnalysis.total_revenue[branchKey]) {
            crossAnalysis.total_revenue[branchKey] = {};
          }
          if (!crossAnalysis.total_revenue[branchKey][productKey]) {
            crossAnalysis.total_revenue[branchKey][productKey] = 0;
          }
          crossAnalysis.total_revenue[branchKey][productKey] += Math.round(staffRevenue * ratio);
        }
      });
    }
  });
  
  Logger.log('✅ 支部×商材クロス分析データを生成: ' + reportPeriod);
  return crossAnalysis;
}

// 特定月のレポート再生成関数
function regenerateMonthlyReport(targetPeriod) {
  Logger.log('🔄 月次レポート再生成開始: ' + targetPeriod);
  
  // 既存ファイルの削除（特定ディレクトリ対応）
  try {
    var targetFolder = getTargetDirectory();
    var folder = null;
    
    // 特定ディレクトリが設定されている場合はそちらを使用
    if (targetFolder) {
      folder = targetFolder;
      Logger.log('📁 特定ディレクトリから既存ファイルを削除: ' + folder.getName());
    } else {
      // 従来のフォルダからも削除
      var folderName = getConfig('file_management.folder_name') || "月次営業分析レポート";
      var folders = DriveApp.getFoldersByName(folderName);
      if (folders.hasNext()) {
        folder = folders.next();
        Logger.log('📁 従来フォルダから既存ファイルを削除: ' + folder.getName());
      }
    }
    
    if (folder) {
      var files = folder.getFiles();
      while (files.hasNext()) {
        var file = files.next();
        var fileName = file.getName();
        
        if (fileName.includes(targetPeriod)) {
          file.setTrashed(true);
          Logger.log('🗑️ 削除: ' + fileName);
        }
      }
    }
  } catch (error) {
    Logger.log('⚠️ 既存ファイル削除エラー: ' + error.message);
  }
  
  // 新しいレポート生成
  return generateMonthlyReport(targetPeriod);
}

// メイン実行関数
function main() {
  // 月次定例報告生成（推奨）
  return generateMonthlyReport();
}

// 従来の全機能実行関数（デバッグ用）
function runAllAnalyses() {
  // 従来のネスト構造JSON生成
  mergeSalesDataNested();
  
  // 基本的な分析用JSON生成
  generateAnalysisJson();
  
  // 詳細分析用JSON生成
  generateDetailedAnalysisJson();
  
  // 定着率分析用JSON生成
  generateRetentionAnalysisJson();
}

// 設定管理用ユーティリティ関数
function updateAlertThresholds(newThresholds) {
  try {
    // 承認率閾値の更新
    if (newThresholds.approval_rate) {
      updateConfig('alerts.approval_rate.warning_threshold', newThresholds.approval_rate.warning || 60);
      updateConfig('alerts.approval_rate.critical_threshold', newThresholds.approval_rate.critical || 50);
    }
    
    // 定着率閾値の更新
    if (newThresholds.retention) {
      updateConfig('alerts.retention.warning_threshold', newThresholds.retention.warning || 70);
      updateConfig('alerts.retention.critical_threshold', newThresholds.retention.critical || 60);
    }
    
    // 高リスク学生数閾値の更新
    if (newThresholds.high_risk_staff) {
      updateConfig('alerts.high_risk_staff.warning_threshold', newThresholds.high_risk_staff.warning || 3);
      updateConfig('alerts.high_risk_staff.critical_threshold', newThresholds.high_risk_staff.critical || 5);
    }
    
    Logger.log('✅ アラート閾値を更新しました');
    return { success: true, message: 'アラート閾値を更新しました' };
    
  } catch (error) {
    Logger.log('❌ アラート閾値更新エラー: ' + error.message);
    return { success: false, error: error.message };
  }
}

function updateRiskScoringWeights(newWeights) {
  try {
    Object.keys(newWeights).forEach(function(weightKey) {
      updateConfig('risk_scoring.weights.' + weightKey, newWeights[weightKey]);
    });
    
    Logger.log('✅ リスクスコアリング重みを更新しました');
    return { success: true, message: 'リスクスコアリング重みを更新しました' };
    
  } catch (error) {
    Logger.log('❌ リスクスコアリング重み更新エラー: ' + error.message);
    return { success: false, error: error.message };
  }
}

function updateRiskScoringFactors(newFactors) {
  try {
    Object.keys(newFactors).forEach(function(factorKey) {
      updateConfig('risk_scoring.factors.' + factorKey, newFactors[factorKey]);
    });
    
    Logger.log('✅ リスクスコアリング要因を更新しました');
    return { success: true, message: 'リスクスコアリング要因を更新しました' };
    
  } catch (error) {
    Logger.log('❌ リスクスコアリング要因更新エラー: ' + error.message);
    return { success: false, error: error.message };
  }
}

function getCurrentConfig() {
  return {
    alerts: getConfig('alerts'),
    risk_scoring: getConfig('risk_scoring'),
    monthly_summary: getConfig('monthly_summary'),
    file_management: getConfig('file_management')
  };
}

function resetConfigToDefaults() {
  try {
    // デフォルト設定を再読み込み
    var defaultConfig = {
      alerts: {
        approval_rate: { warning_threshold: 60, critical_threshold: 50 },
        retention: { warning_threshold: 70, critical_threshold: 60 },
        high_risk_staff: { warning_threshold: 3, critical_threshold: 5 },
        activity: { min_calls_per_month: 50, min_hours_per_month: 4, min_activity_days: 5 }
      },
      risk_scoring: {
        weights: {
          low_activity_rate: 30,
          recent_inactivity: 25,
          low_performance: 20,
          short_tenure_low_activity: 15,
          unstable_activity: 10
        },
        thresholds: { high_risk: 50, medium_risk: 30 },
        factors: {
          activity_rate_threshold: 50,
          recent_activity_days_threshold: 5,
          appointment_rate_threshold: 2,
          short_tenure_months: 3,
          min_activity_days_short_tenure: 10,
          activity_variance_threshold: 10
        }
      },
      monthly_summary: { top_staff_count: 10 },
      file_management: {
        folder_name: "月次営業分析レポート",
        file_naming: {
          summary: "月次サマリー_",
          retention: "定着率分析_",
          detailed: "詳細分析_",
          basic: "基本分析_",
          log: "実行ログ_"
        }
      }
    };
    
    // 設定を更新
    Object.keys(defaultConfig).forEach(function(section) {
      Object.keys(defaultConfig[section]).forEach(function(key) {
        if (typeof defaultConfig[section][key] === 'object') {
          Object.keys(defaultConfig[section][key]).forEach(function(subKey) {
            updateConfig(section + '.' + key + '.' + subKey, defaultConfig[section][key][subKey]);
          });
        } else {
          updateConfig(section + '.' + key, defaultConfig[section][key]);
        }
      });
    });
    
    Logger.log('✅ 設定をデフォルトにリセットしました');
    return { success: true, message: '設定をデフォルトにリセットしました' };
    
  } catch (error) {
    Logger.log('❌ 設定リセットエラー: ' + error.message);
    return { success: false, error: error.message };
  }
}

// 設定変更のテスト実行
function testConfigChanges() {
  Logger.log('🧪 設定変更のテスト実行開始');
  
  // 現在の設定を取得
  var currentConfig = getCurrentConfig();
  Logger.log('現在の設定: ' + JSON.stringify(currentConfig, null, 2));
  
  // 設定変更のテスト
  var testThresholds = {
    approval_rate: { warning: 65, critical: 55 },
    retention: { warning: 75, critical: 65 },
    high_risk_staff: { warning: 4, critical: 6 }
  };
  
  var result = updateAlertThresholds(testThresholds);
  Logger.log('テスト結果: ' + JSON.stringify(result, null, 2));
  
  // 設定を元に戻す
  resetConfigToDefaults();
  
  Logger.log('✅ 設定変更テスト完了');
  return result;
}

// ========================================
// 使用例
// ========================================

// 1. 特定ディレクトリを設定して全月分のJSONを生成
function generateAllPeriodJsonToTargetDirectory() {
  // 特定ディレクトリを有効化
  enableTargetDirectory();
  
  // 基本分析（全月分）
  generateAnalysisJson();
  
  // 定着率分析（全月分）
  generateRetentionAnalysisJson();
  
  // 詳細分析（全月分）
  generateAllPeriodDetailedAnalysisJson();
  
  Logger.log('✅ 全月分のJSONを特定ディレクトリに生成しました');
}

// 2. 全月データ用ディレクトリを設定して全月分のJSONを生成（統一：インサイドセールス分析データフォルダを使用）
function generateAllPeriodJsonToAllPeriodDirectory() {
  Logger.log('📁 注意：全月データはインサイドセールス分析データフォルダに統一されました');
  
  // インサイドセールス分析データフォルダを使用（統一）
  return generateAllPeriodJsonToTargetDirectory();
}

// 3. フォルダIDを指定して特定ディレクトリを設定
function setTargetDirectoryByFolderId(folderId) {
  var result = updateTargetDirectory({
    enabled: true,
    folder_id: folderId,
    create_if_not_exists: false
  });
  
  if (result.success) {
    Logger.log('✅ 特定ディレクトリを設定しました: ' + folderId);
  } else {
    Logger.log('❌ 特定ディレクトリの設定に失敗しました: ' + result.error);
  }
  
  return result;
}

// 4. フォルダ名を指定して特定ディレクトリを設定
function setTargetDirectoryByFolderName(folderName) {
  var result = updateTargetDirectory({
    enabled: true,
    folder_name: folderName,
    create_if_not_exists: true
  });
  
  if (result.success) {
    Logger.log('✅ 特定ディレクトリを設定しました: ' + folderName);
  } else {
    Logger.log('❌ 特定ディレクトリの設定に失敗しました: ' + result.error);
  }
  
  return result;
}

// 5. フォルダIDを指定して全月データ用ディレクトリを設定
function setAllPeriodDirectoryByFolderId(folderId) {
  var result = updateAllPeriodDirectory({
    enabled: true,
    folder_id: folderId,
    create_if_not_exists: false
  });
  
  if (result.success) {
    Logger.log('✅ 全月データ用ディレクトリを設定しました: ' + folderId);
  } else {
    Logger.log('❌ 全月データ用ディレクトリの設定に失敗しました: ' + result.error);
  }
  
  return result;
}

// 6. フォルダ名を指定して全月データ用ディレクトリを設定
function setAllPeriodDirectoryByFolderName(folderName) {
  var result = updateAllPeriodDirectory({
    enabled: true,
    folder_name: folderName,
    create_if_not_exists: true
  });
  
  if (result.success) {
    Logger.log('✅ 全月データ用ディレクトリを設定しました: ' + folderName);
  } else {
    Logger.log('❌ 全月データ用ディレクトリの設定に失敗しました: ' + result.error);
  }
  
  return result;
}

// 7. 特定ディレクトリを無効化してマイドライブに保存
function disableTargetDirectoryAndSaveToMyDrive() {
  disableTargetDirectory();
  
  // 基本分析（全月分）
  generateAnalysisJson();
  
  // 定着率分析（全月分）
  generateRetentionAnalysisJson();
  
  // 詳細分析（全月分）
  generateAllPeriodDetailedAnalysisJson();
  
  Logger.log('✅ 全月分のJSONをマイドライブに生成しました');
}

// 8. 全月データ用ディレクトリを無効化してマイドライブに保存（統一：特定ディレクトリを無効化）
function disableAllPeriodDirectoryAndSaveToMyDrive() {
  Logger.log('📁 注意：全月データ機能は廃止され、特定ディレクトリ機能に統一されました');
  
  // 特定ディレクトリを無効化してマイドライブに保存（統一）
  return disableTargetDirectoryAndSaveToMyDrive();
}

// 全期間サマリー（全月分をまとめた詳細分析JSON）を1つだけ出力する関数
function generateAllPeriodDetailedAnalysisJson() {
  // 基本的な分析JSONを取得（全期間分）
  var basicAnalysis = generateAnalysisJson(); // これが全期間分
  // 詳細分析データを追加
  var detailedAnalysis = {
    ...basicAnalysis,
    detailed_metrics: {
      acquisition_analysis: {
        new_customers: {},
        existing_customers: {},
        acquisition_efficiency: {}
      },
      activity_efficiency: {
        calls_per_hour: {},
        appointments_per_call: {},
        deals_per_appointment: {},
        revenue_per_deal: {}
      },
      trend_analysis: {
        monthly_trends: {},
        branch_comparison: {},
        product_performance: {}
      }
    }
  };
  // ここで詳細分析の計算処理（generateDetailedAnalysisJsonと同じ内容）を実施
  // ...（必要なら詳細分析のロジックをここにコピー）...
  // 全期間サマリーとして保存
  var json = JSON.stringify(detailedAnalysis, null, 2);
  var fileName = 'detailed_sales_analysis_all.json';
  var file = saveFileToAllPeriodDirectory(fileName, json);
  Logger.log('✅ 全期間詳細分析用JSON出力完了: ' + file.getUrl());
  return detailedAnalysis;
}

// 特定ディレクトリの設定を変更する関数
function updateTargetDirectory(newConfig) {
  try {
    if (newConfig.enabled !== undefined) {
      updateConfig('file_management.target_directory.enabled', newConfig.enabled);
    }
    if (newConfig.folder_id !== undefined) {
      updateConfig('file_management.target_directory.folder_id', newConfig.folder_id);
    }
    if (newConfig.folder_name !== undefined) {
      updateConfig('file_management.target_directory.folder_name', newConfig.folder_name);
    }
    if (newConfig.create_if_not_exists !== undefined) {
      updateConfig('file_management.target_directory.create_if_not_exists', newConfig.create_if_not_exists);
    }
    
    Logger.log('✅ 特定ディレクトリ設定を更新しました');
    return { success: true, message: '特定ディレクトリ設定を更新しました' };
    
  } catch (error) {
    Logger.log('❌ 特定ディレクトリ設定更新エラー: ' + error.message);
    return { success: false, error: error.message };
  }
}

// 特定ディレクトリの設定を取得する関数
function getTargetDirectoryConfig() {
  return getConfig('file_management.target_directory');
}

// 特定ディレクトリを無効化する関数
function disableTargetDirectory() {
  return updateTargetDirectory({ enabled: false });
}

// 特定ディレクトリを有効化する関数
function enableTargetDirectory() {
  return updateTargetDirectory({ enabled: true });
}

// 設定変更のテスト実行
function testConfigChanges() {
  Logger.log('🧪 設定変更のテスト実行開始');
  
  // 現在の設定を取得
  var currentConfig = getCurrentConfig();
  Logger.log('現在の設定: ' + JSON.stringify(currentConfig, null, 2));
  
  // 設定変更のテスト
  var testThresholds = {
    approval_rate: { warning: 65, critical: 55 },
    retention: { warning: 75, critical: 65 },
    high_risk_staff: { warning: 4, critical: 6 }
  };
  
  var result = updateAlertThresholds(testThresholds);
  Logger.log('テスト結果: ' + JSON.stringify(result, null, 2));
  
  // 設定を元に戻す
  resetConfigToDefaults();
  
  Logger.log('✅ 設定変更テスト完了');
  return result;
}

// 全月データ用ディレクトリの設定を変更する関数
function updateAllPeriodDirectory(newConfig) {
  try {
    if (newConfig.enabled !== undefined) {
      updateConfig('file_management.all_period_directory.enabled', newConfig.enabled);
    }
    if (newConfig.folder_id !== undefined) {
      updateConfig('file_management.all_period_directory.folder_id', newConfig.folder_id);
    }
    if (newConfig.folder_name !== undefined) {
      updateConfig('file_management.all_period_directory.folder_name', newConfig.folder_name);
    }
    if (newConfig.create_if_not_exists !== undefined) {
      updateConfig('file_management.all_period_directory.create_if_not_exists', newConfig.create_if_not_exists);
    }
    
    Logger.log('✅ 全月データ用ディレクトリ設定を更新しました');
    return { success: true, message: '全月データ用ディレクトリ設定を更新しました' };
    
  } catch (error) {
    Logger.log('❌ 全月データ用ディレクトリ設定更新エラー: ' + error.message);
    return { success: false, error: error.message };
  }
}

// 全月データ用ディレクトリの設定を取得する関数
function getAllPeriodDirectoryConfig() {
  return getConfig('file_management.all_period_directory');
}

// 全月データ用ディレクトリを無効化する関数
function disableAllPeriodDirectory() {
  return updateAllPeriodDirectory({ enabled: false });
}

// 全月データ用ディレクトリを有効化する関数
function enableAllPeriodDirectory() {
  return updateAllPeriodDirectory({ enabled: true });
}

// 月次レポート最適化保存関数（全月データファイルを除外）
function saveMonthlyReportsOptimized(reportPeriod, analysisData, detailedData, retentionData, monthlySummary) {
  try {
    // 1) 特定ディレクトリまたは月次レポート用フォルダを取得
    var folder = getTargetDirectory();
    var folderName = getConfig('file_management.folder_name') || "月次営業分析レポート";
    var fileNaming = getConfig('file_management.file_naming') || {};
    
    // 特定ディレクトリが設定されていない場合は従来の方法でフォルダを取得
    if (!folder) {
      var folders = DriveApp.getFoldersByName(folderName);
      if (folders.hasNext()) {
        folder = folders.next();
      } else {
        folder = DriveApp.createFolder(folderName);
        Logger.log('📁 フォルダ作成: ' + folderName);
      }
    }
    
    // 2) 月次JSONファイルを保存（全月データファイルは生成済みなので除外）
    var files = [];
    
    // 月次サマリー
    if (monthlySummary) {
      var summaryJson = JSON.stringify(monthlySummary, null, 2);
      var summaryFileName = (fileNaming.summary || "月次サマリー_") + reportPeriod + '.json';
      var summaryBlob = Utilities.newBlob(summaryJson, 'application/json', summaryFileName);
      var summaryFile = folder.createFile(summaryBlob);
      files.push(summaryFile.getName());
      Logger.log('📄 月次サマリー保存: ' + summaryFile.getName());
    }
    
    // 定着率分析（月次版）
    if (retentionData) {
      var retentionJson = JSON.stringify(retentionData, null, 2);
      var retentionFileName = (fileNaming.retention || "定着率分析_") + reportPeriod + '.json';
      var retentionBlob = Utilities.newBlob(retentionJson, 'application/json', retentionFileName);
      var retentionFile = folder.createFile(retentionBlob);
      files.push(retentionFile.getName());
      Logger.log('📄 定着率分析保存: ' + retentionFile.getName());
    }
    
    // 詳細分析（月次版）
    if (detailedData) {
      var detailedJson = JSON.stringify(detailedData, null, 2);
      var detailedFileName = (fileNaming.detailed || "詳細分析_") + reportPeriod + '.json';
      var detailedBlob = Utilities.newBlob(detailedJson, 'application/json', detailedFileName);
      var detailedFile = folder.createFile(detailedBlob);
      files.push(detailedFile.getName());
      Logger.log('📄 詳細分析保存: ' + detailedFile.getName());
    }
    
    // 基本分析（月次版）
    if (analysisData) {
      var analysisJson = JSON.stringify(analysisData, null, 2);
      var analysisFileName = (fileNaming.basic || "基本分析_") + reportPeriod + '.json';
      var analysisBlob = Utilities.newBlob(analysisJson, 'application/json', analysisFileName);
      var analysisFile = folder.createFile(analysisBlob);
      files.push(analysisFile.getName());
      Logger.log('📄 基本分析保存: ' + analysisFile.getName());
    }
    
    // 3) 実行ログファイルを作成
    var logData = {
      execution_time: new Date().toISOString(),
      report_period: reportPeriod,
      files_created: files,
      folder_url: folder.getUrl(),
      config_version: getConfig('metadata.version') || '1.0',
      optimization: "monthly_specific_files_only",
      summary: {
        total_staff: retentionData ? Object.keys(retentionData.staff_retention_analysis).length : 0,
        total_calls: analysisData ? analysisData.summary_by_period.total_calls : 0,
        total_deals: analysisData ? analysisData.summary_by_period.total_deals : 0,
        approval_rate: analysisData ? analysisData.summary_by_period.overall_approval_rate : 0
      }
    };
    
    var logJson = JSON.stringify(logData, null, 2);
    var logFileName = (fileNaming.log || "実行ログ_") + reportPeriod + '.json';
    var logBlob = Utilities.newBlob(logJson, 'application/json', logFileName);
    var logFile = folder.createFile(logBlob);
    files.push(logFile.getName());
    
    Logger.log('✅ 月次レポート保存完了（最適化版）: ' + reportPeriod);
    Logger.log('📄 作成ファイル数: ' + files.length);
    
    return {
      folder: folder,
      files: files,
      log: logFile
    };
  } catch (error) {
    Logger.log('❌ ファイル保存エラー: ' + error.message);
    throw error;
  }
}