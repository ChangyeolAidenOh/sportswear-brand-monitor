"""
Stage 6 Forecasting — Track B: LSTM Encoder-Decoder Forecast

2-layer LSTM (hidden_size=64) with dropout + early stopping.
Input features: search_index, CSI, week_of_year, quarter.
Lookback window: 13 weeks (one quarterly cycle).

Inputs:
    data/forecast/nb_korea_forecast_data.csv
    data/forecast/nb_global_forecast_data.csv

Outputs:
    data/forecast/lstm_forecast_korea.csv
    data/forecast/lstm_forecast_global.csv
    data/forecast/lstm_metrics.csv
    data/forecast/lstm_training_log_korea.csv
    data/forecast/lstm_training_log_global.csv
    figures/forecast/nb_korea_lstm_forecast.png
    figures/forecast/nb_global_lstm_forecast.png
    figures/forecast/nb_korea_lstm_loss.png
    figures/forecast/nb_global_lstm_loss.png

Usage:
    python -m analysis.forecast_lstm
"""

# stdlib
import os
import warnings

# third-party
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler

# 수정 1: import 아래에 Fourier 함수 추가 (SARIMAX와 동일)
FOURIER_CONFIG = {52: 2, 13: 2}

def make_fourier_terms(n, period_k_map, start_idx=0):
    """Generate Fourier sin/cos terms (identical to SARIMAX)."""
    t = np.arange(start_idx, start_idx + n)
    cols = {}
    for period, K in period_k_map.items():
        for k in range(1, K + 1):
            cols[f"sin_{period}_{k}"] = np.sin(2 * np.pi * k * t / period)
            cols[f"cos_{period}_{k}"] = np.cos(2 * np.pi * k * t / period)
    return pd.DataFrame(cols)

warnings.filterwarnings("ignore", category=FutureWarning)

plt.rcParams.update({
    "font.family": "AppleGothic",
    "axes.unicode_minus": False,
    "figure.dpi": 150,
    "figure.figsize": (14, 5),
    "axes.grid": True,
    "grid.alpha": 0.3,
})

# ================================================================
# Constants
# ================================================================
DATA_DIR = "data/forecast"
FIG_DIR = "figures/forecast"
REGIONS = ["korea", "global"]

LOOKBACK = 13
HIDDEN_SIZE = 64
NUM_LAYERS = 2
DROPOUT = 0.3
LEARNING_RATE = 0.001
MAX_EPOCHS = 500
PATIENCE = 30
VAL_RATIO = 0.15  # validation split from train

SEED = 42
torch.manual_seed(SEED)
np.random.seed(SEED)

# ================================================================
# Sequence creation
# ================================================================
def create_sequences(data, target_col_idx, lookback):
    """Create input sequences and targets for LSTM.

    Args:
        data: 2D numpy array (n_samples, n_features), already scaled
        target_col_idx: index of the target column in data
        lookback: number of past steps to use as input

    Returns:
        X: (n_sequences, lookback, n_features)
        y: (n_sequences,) — next-step target
    """
    X, y = [], []
    for i in range(lookback, len(data)):
        X.append(data[i - lookback:i, :])
        y.append(data[i, target_col_idx])
    return np.array(X), np.array(y)


# ================================================================
# LSTM Model
# ================================================================
class LSTMForecaster(nn.Module):
    """2-layer LSTM for time series forecasting."""

    def __init__(self, input_size, hidden_size, num_layers, dropout):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            batch_first=True,
        )
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        last_hidden = lstm_out[:, -1, :]  # last time step
        return self.fc(last_hidden).squeeze(-1)


# ================================================================
# Training loop with early stopping
# ================================================================
def train_model(model, X_train, y_train, X_val, y_val):
    """Train LSTM with early stopping on validation loss."""
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    criterion = nn.MSELoss()

    best_val_loss = float("inf")
    epochs_no_improve = 0
    best_state = None
    history = {"epoch": [], "train_loss": [], "val_loss": []}

    for epoch in range(MAX_EPOCHS):
        # Train
        model.train()
        optimizer.zero_grad()
        pred = model(X_train)
        loss = criterion(pred, y_train)
        loss.backward()
        optimizer.step()

        # Validate
        model.eval()
        with torch.no_grad():
            val_pred = model(X_val)
            val_loss = criterion(val_pred, y_val)

        history["epoch"].append(epoch + 1)
        history["train_loss"].append(loss.item())
        history["val_loss"].append(val_loss.item())

        # Early stopping
        if val_loss.item() < best_val_loss:
            best_val_loss = val_loss.item()
            epochs_no_improve = 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            epochs_no_improve += 1

        if epochs_no_improve >= PATIENCE:
            print(f"  Early stopping at epoch {epoch + 1} (best val_loss={best_val_loss:.6f})")
            break

        if (epoch + 1) % 50 == 0:
            print(f"  Epoch {epoch + 1}: train={loss.item():.6f}, val={val_loss.item():.6f}")

    # Restore best model
    if best_state is not None:
        model.load_state_dict(best_state)

    return model, pd.DataFrame(history)


# ================================================================
# Recursive multi-step forecast
# ================================================================
def recursive_forecast(model, last_sequence, n_steps, scaler, feature_data, target_col_idx):
    """Generate n_steps forecast recursively.

    Args:
        model: trained LSTM
        last_sequence: (lookback, n_features) scaled array — last known window
        n_steps: forecast horizon
        scaler: fitted MinMaxScaler
        feature_data: (n_steps, n_features) scaled future features (CSI, temporal)
        target_col_idx: index of search_index in feature array
    """
    model.eval()
    predictions = []
    current_seq = last_sequence.copy()

    with torch.no_grad():
        for step in range(n_steps):
            x = torch.FloatTensor(current_seq).unsqueeze(0)
            pred_scaled = model(x).item()
            predictions.append(pred_scaled)

            # Build next input row: use future features + predicted target
            next_row = feature_data[step, :].copy()
            next_row[target_col_idx] = pred_scaled

            # Slide window
            current_seq = np.vstack([current_seq[1:, :], next_row.reshape(1, -1)])

    # Inverse transform predictions
    dummy = np.zeros((len(predictions), scaler.n_features_in_))
    dummy[:, target_col_idx] = predictions
    inv = scaler.inverse_transform(dummy)
    return inv[:, target_col_idx]


# ================================================================
# Evaluation metrics
# ================================================================
def compute_metrics(actual, predicted, label=""):
    """Compute RMSE, MAE, MAPE (excluding zeros)."""
    residuals = actual - predicted
    rmse = np.sqrt(np.mean(residuals ** 2))
    mae = np.mean(np.abs(residuals))

    nonzero_mask = actual != 0
    if nonzero_mask.sum() > 0:
        mape = np.mean(np.abs(residuals[nonzero_mask] / actual[nonzero_mask])) * 100
    else:
        mape = np.nan

    return {"label": label, "rmse": rmse, "mae": mae, "mape_pct": mape}


# ================================================================
# Plot: forecast
# ================================================================
def plot_forecast(train_df, test_df, forecast_values, region, metrics):
    """Plot actual vs LSTM forecast."""
    fig, ax = plt.subplots(figsize=(14, 5))

    ax.plot(train_df["week_start"], train_df["search_index"],
            color="#888888", linewidth=0.8, label="Train")
    ax.plot(test_df["week_start"], test_df["search_index"],
            color="#E74C3C", linewidth=1.5, label="Actual (Test)")
    ax.plot(test_df["week_start"], forecast_values,
            color="#2ECC71", linewidth=1.5, linestyle="--", label="LSTM Forecast")

    ax.axvline(train_df["week_start"].iloc[-1], color="gray", linestyle="--", alpha=0.5)

    anomaly_test = test_df[test_df["is_anomaly_week"] == 1]
    if len(anomaly_test) > 0:
        ax.scatter(anomaly_test["week_start"], anomaly_test["search_index"],
                   color="red", marker="x", s=80, zorder=5, label="Anomaly Week")

    region_label = "Korea" if region == "korea" else "Global"
    ax.set_title(
        f"NB {region_label} — LSTM Forecast (2-layer, h={HIDDEN_SIZE}, lookback={LOOKBACK})\n"
        f"RMSE={metrics['rmse']:.2f}  MAE={metrics['mae']:.2f}  MAPE={metrics['mape_pct']:.1f}%"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Search Index")
    ax.legend(loc="upper left", fontsize=9)

    fig_path = os.path.join(FIG_DIR, f"nb_{region}_lstm_forecast.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {fig_path}")


# ================================================================
# Plot: training loss
# ================================================================
def plot_loss(history_df, region):
    """Plot training and validation loss curves."""
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(history_df["epoch"], history_df["train_loss"], label="Train Loss", linewidth=0.8)
    ax.plot(history_df["epoch"], history_df["val_loss"], label="Val Loss", linewidth=0.8)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("MSE Loss")

    region_label = "Korea" if region == "korea" else "Global"
    ax.set_title(f"NB {region_label} — LSTM Training Loss")
    ax.legend()

    fig_path = os.path.join(FIG_DIR, f"nb_{region}_lstm_loss.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {fig_path}")


# ================================================================
# Main
# ================================================================
if __name__ == "__main__":
    all_metrics = []
    feature_cols = ["search_index", "csi",
                    "sin_52_1", "cos_52_1", "sin_52_2", "cos_52_2",
                    "sin_13_1", "cos_13_1", "sin_13_2", "cos_13_2"]
    target_col_idx = 0  # search_index

    for region in REGIONS:
        print(f"\n{'='*60}")
        print(f"NB {region.upper()} — LSTM Forecast")
        print(f"{'='*60}")

        # Load data
        csv_path = os.path.join(DATA_DIR, f"nb_{region}_forecast_data.csv")
        df = pd.read_csv(csv_path, parse_dates=["week_start"])
        fourier_all = make_fourier_terms(len(df), FOURIER_CONFIG, start_idx=0)
        for col in fourier_all.columns:
            df[col] = fourier_all[col].values

        train_full = df[df["split"] == "train"].copy().reset_index(drop=True)
        test = df[df["split"] == "test"].copy().reset_index(drop=True)

        # Scale features
        scaler = MinMaxScaler()
        train_scaled = scaler.fit_transform(train_full[feature_cols].values)
        test_scaled = scaler.transform(test[feature_cols].values)

        # Train/Val split from train_full
        n_val = max(1, int(len(train_scaled) * VAL_RATIO))
        train_data = train_scaled[:-n_val]
        val_data = train_scaled[-n_val:]

        # Create sequences
        X_train, y_train = create_sequences(train_data, target_col_idx, LOOKBACK)
        X_val, y_val = create_sequences(
            np.vstack([train_data[-(LOOKBACK):], val_data]),
            target_col_idx, LOOKBACK
        )

        print(f"  Train sequences: {X_train.shape[0]}, Val sequences: {X_val.shape[0]}")
        print(f"  Features: {feature_cols}")

        # Convert to tensors
        X_train_t = torch.FloatTensor(X_train)
        y_train_t = torch.FloatTensor(y_train)
        X_val_t = torch.FloatTensor(X_val)
        y_val_t = torch.FloatTensor(y_val)

        # Build and train model
        n_features = X_train.shape[2]
        model = LSTMForecaster(n_features, HIDDEN_SIZE, NUM_LAYERS, DROPOUT)
        print(f"  Model params: {sum(p.numel() for p in model.parameters()):,}")

        model, history = train_model(model, X_train_t, y_train_t, X_val_t, y_val_t)

        # Save training log
        log_path = os.path.join(DATA_DIR, f"lstm_training_log_{region}.csv")
        history.to_csv(log_path, index=False)

        # Recursive forecast on test period
        # Last known sequence = last LOOKBACK rows of full train (scaled)
        last_seq = train_scaled[-LOOKBACK:]
        forecast_values = recursive_forecast(
            model, last_seq, len(test), scaler, test_scaled, target_col_idx
        )

        # Evaluation
        actual = test["search_index"].values
        metrics_all = compute_metrics(actual, forecast_values, f"{region}_all")
        print(f"\n  Overall: RMSE={metrics_all['rmse']:.2f}, MAE={metrics_all['mae']:.2f}, MAPE={metrics_all['mape_pct']:.1f}%")

        anomaly_mask = test["is_anomaly_week"].values == 1
        if anomaly_mask.sum() > 0:
            metrics_anom = compute_metrics(actual[anomaly_mask], forecast_values[anomaly_mask], f"{region}_anomaly")
            print(f"  Anomaly weeks ({anomaly_mask.sum()}): RMSE={metrics_anom['rmse']:.2f}")
            all_metrics.append(metrics_anom)

        non_anomaly_mask = ~anomaly_mask
        if non_anomaly_mask.sum() > 0:
            metrics_normal = compute_metrics(actual[non_anomaly_mask], forecast_values[non_anomaly_mask], f"{region}_normal")
            print(f"  Normal weeks ({non_anomaly_mask.sum()}): RMSE={metrics_normal['rmse']:.2f}")
            all_metrics.append(metrics_normal)

        all_metrics.append(metrics_all)

        # Save forecast
        forecast_df = test[["week_start", "search_index", "is_anomaly_week"]].copy()
        forecast_df["lstm_forecast"] = forecast_values
        forecast_df["lstm_error"] = actual - forecast_values
        forecast_csv = os.path.join(DATA_DIR, f"lstm_forecast_{region}.csv")
        forecast_df.to_csv(forecast_csv, index=False)
        print(f"  Saved: {forecast_csv}")

        # Plots
        plot_forecast(train_full, test, forecast_values, region, metrics_all)
        plot_loss(history, region)

    # Save metrics
    metrics_df = pd.DataFrame(all_metrics)
    metrics_path = os.path.join(DATA_DIR, "lstm_metrics.csv")
    metrics_df.to_csv(metrics_path, index=False)
    print(f"\nSaved: {metrics_path}")
    print("\nTrack B LSTM complete.")
