// 営業分析システム設定ファイル
// このファイルで閾値や設定値を管理します

var CONFIG = {
  // アラート閾値設定
  alerts: {
    // 承認率関連
    approval_rate: {
      warning_threshold: 60,    // 警告レベル（%）
      critical_threshold: 50    // 危険レベル（%）
    },
    
    // 定着率関連
    retention: {
      warning_threshold: 30,    // 警告レベル（%）
      critical_threshold: 20    // 危険レベル（%）
    },
    
    // 高リスク学生数
    high_risk_staff: {
      warning_threshold: 10,     // 警告レベル（名）
      critical_threshold: 15     // 危険レベル（名）
    },
    
    // 活動量関連
    activity: {
      min_calls_per_month: 5,  // 月次最小架電数
      min_hours_per_month: 1,   // 月次最小架電時間
      min_activity_days: 2      // 月次最小活動日数
    }
  },
  
  // 離脱リスクスコアリング設定
  risk_scoring: {
    // リスク要因の重み付け
    weights: {
      low_activity_rate: 50,    // 活動率が低い
      recent_inactivity: 10,    // 最近の活動が少ない
      low_performance: 40,      // 成果が低い
      short_tenure_low_activity: 15, // 在籍期間が短いが活動が少ない
      unstable_activity: 10     // 活動の安定性が低い
    },
    
    // リスクレベル判定閾値
    thresholds: {
      high_risk: 50,            // 高リスク判定閾値
      medium_risk: 30           // 中リスク判定閾値
    },
    
    // リスク要因の詳細設定
    factors: {
      activity_rate_threshold: 50,      // 活動率警告閾値（%）
      recent_activity_days_threshold: 5, // 最近3ヶ月の最小活動日数
      appointment_rate_threshold: 2,     // アポ獲得率警告閾値（%）
      short_tenure_months: 3,           // 短期在籍の定義（ヶ月）
      min_activity_days_short_tenure: 10, // 短期在籍者の最小活動日数
      activity_variance_threshold: 10   // 活動ばらつき警告閾値
    }
  },
  
  // 月次サマリー設定
  monthly_summary: {
    // 個人別パフォーマンス表示件数
    top_staff_count: 10,
    
    // 効率性指標の表示設定
    efficiency_metrics: {
      show_calls_per_hour: true,
      show_appointments_per_call: true,
      show_deals_per_appointment: true
    }
  },
  
  // ファイル管理設定
  file_management: {
    // フォルダ名
    folder_name: "月次営業分析レポート",
    
    // 特定ディレクトリの設定
    target_directory: {
      enabled: true,  // 特定ディレクトリを使用するかどうか
      folder_id: "",  // 特定のフォルダID（空の場合はフォルダ名で検索）
      folder_name: "インサイドセールス分析データ",  // 特定のフォルダ名
      create_if_not_exists: true  // フォルダが存在しない場合に作成するかどうか
    },
    
    // 全月データ用のフォルダ設定
    all_period_directory: {
      enabled: true,  // 全月データ用ディレクトリを使用するかどうか
      folder_id: "",  // 特定のフォルダID（空の場合はフォルダ名で検索）
      folder_name: "全月データ",  // 全月データ用のフォルダ名
      create_if_not_exists: true  // フォルダが存在しない場合に作成するかどうか
    },
    
    // ファイル命名規則
    file_naming: {
      summary: "月次サマリー_",
      retention: "定着率分析_",
      detailed: "詳細分析_",
      basic: "基本分析_",
      log: "実行ログ_"
    },
    
    // ファイル保持期間（月）
    retention_period: 12
  },
  
  // データ処理設定
  data_processing: {
    // 日付形式
    date_format: "YYYY-MM-DD",
    
    // 数値の小数点以下桁数
    decimal_places: 2,
    
    // 欠損値の処理
    missing_value_handling: "zero" // "zero", "null", "skip"
  },
  
  // ログ設定
  logging: {
    // ログレベル
    level: "info", // "debug", "info", "warning", "error"
    
    // ログ出力設定
    output: {
      console: true,
      file: true,
      email: false
    }
  }
};

// 設定値取得用ヘルパー関数
function getConfig(path) {
  var keys = path.split('.');
  var value = CONFIG;
  
  for (var i = 0; i < keys.length; i++) {
    if (value && typeof value === 'object' && keys[i] in value) {
      value = value[keys[i]];
    } else {
      return null;
    }
  }
  
  return value;
}

// 設定値更新用ヘルパー関数
function updateConfig(path, newValue) {
  var keys = path.split('.');
  var config = CONFIG;
  
  for (var i = 0; i < keys.length - 1; i++) {
    if (config && typeof config === 'object' && keys[i] in config) {
      config = config[keys[i]];
    } else {
      throw new Error('Invalid config path: ' + path);
    }
  }
  
  config[keys[keys.length - 1]] = newValue;
  return true;
}

// 設定値の検証
function validateConfig() {
  var errors = [];
  
  // 必須設定のチェック
  if (!CONFIG.alerts || !CONFIG.risk_scoring) {
    errors.push('Required config sections are missing');
  }
  
  // 閾値の妥当性チェック
  if (CONFIG.alerts.approval_rate.warning_threshold < CONFIG.alerts.approval_rate.critical_threshold) {
    errors.push('Approval rate warning threshold should be higher than critical threshold');
  }
  
  if (CONFIG.risk_scoring.thresholds.high_risk < CONFIG.risk_scoring.thresholds.medium_risk) {
    errors.push('High risk threshold should be higher than medium risk threshold');
  }
  
  return {
    valid: errors.length === 0,
    errors: errors
  };
}

// 設定値のエクスポート（バックアップ用）
function exportConfig() {
  return JSON.stringify(CONFIG, null, 2);
}

// 設定値のインポート（復元用）
function importConfig(configJson) {
  try {
    var newConfig = JSON.parse(configJson);
    CONFIG = newConfig;
    return validateConfig();
  } catch (error) {
    return {
      valid: false,
      errors: ['Invalid JSON format: ' + error.message]
    };
  }
} 