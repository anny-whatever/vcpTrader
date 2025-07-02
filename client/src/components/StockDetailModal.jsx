import React from "react";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Chip,
  Card,
  CardBody,
  Progress,
} from "@nextui-org/react";

const StockDetailModal = ({ isOpen, onClose, stockData }) => {
  if (!stockData) return null;

  // Debug logging for SMA values
  console.log('StockDetailModal - SMA Debug:', {
    symbol: stockData.symbol,
    sma_50: stockData.sma_50,
    sma_100: stockData.sma_100,
    sma_200: stockData.sma_200,
    raw_stockData: stockData
  });

  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    try {
      return new Date(dateString).toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return dateString;
    }
  };

  const formatCurrency = (value) => {
    if (value == null || isNaN(value)) return "₹0.00";
    return `₹${parseFloat(value).toFixed(2)}`;
  };

  const formatPercent = (value) => {
    if (value == null || isNaN(value)) return "0.00%";
    return `${parseFloat(value).toFixed(2)}%`;
  };

  const formatNumber = (value, decimals = 2) => {
    if (value == null || isNaN(value)) return "0";
    return parseFloat(value).toFixed(decimals);
  };

  const formatVolume = (value) => {
    if (value == null || isNaN(value)) return "0";
    const num = parseFloat(value);
    if (num >= 10000000) return `${(num / 10000000).toFixed(1)}Cr`;
    if (num >= 100000) return `${(num / 100000).toFixed(1)}L`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toFixed(0);
  };

  const getQualityColor = (score) => {
    if (score >= 7) return "success";
    if (score >= 5) return "warning";
    if (score >= 3) return "default";
    return "danger";
  };

  const getGradeColor = (grade) => {
    switch (grade) {
      case 'A': return "success";
      case 'B': return "primary";
      case 'C': return "warning";
      default: return "danger";
    }
  };

  const getScoreColor = (score, maxScore = 10) => {
    const percentage = (score / maxScore) * 100;
    if (percentage >= 80) return "success";
    if (percentage >= 60) return "primary";
    if (percentage >= 40) return "warning";
    return "danger";
  };

  const contractionDetails = stockData.additional_metrics?.contraction_details || [];
  const weeklyBreakdown = stockData.additional_metrics?.pattern_weekly_breakdown || [];

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose}
      size="5xl"
      scrollBehavior="inside"
      backdrop="opaque"
      className="vcp-detail-modal"
      classNames={{
        backdrop: "bg-zinc-950/80 backdrop-blur-md vcp-modal-backdrop",
        wrapper: "vcp-modal-wrapper",
        base: "bg-zinc-900/95 backdrop-blur-xl border border-zinc-700/50 shadow-2xl vcp-modal-base",
        header: "bg-zinc-800/70 backdrop-blur-sm border-b border-zinc-700/50",
        body: "bg-zinc-900/95 backdrop-blur-sm p-6",
        footer: "bg-zinc-800/70 backdrop-blur-sm border-t border-zinc-700/50",
        closeButton: "hover:bg-zinc-700/50 text-zinc-400 hover:text-white transition-colors"
      }}
      style={{
        zIndex: 100000
      }}
      motionProps={{
        variants: {
          enter: {
            y: 0,
            opacity: 1,
            scale: 1,
            transition: {
              duration: 0.3,
              ease: "easeOut",
            },
          },
          exit: {
            y: -20,
            opacity: 0,
            scale: 0.95,
            transition: {
              duration: 0.2,
              ease: "easeIn",
            },
          },
        }
      }}
    >
      <ModalContent>
        <ModalHeader className="flex flex-col gap-1 border-b border-zinc-700/50">
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-gradient-to-br from-blue-600/20 to-purple-600/20 border border-blue-500/30">
                  <svg className="w-6 h-6 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M2 10a8 8 0 018-8v8h8a8 8 0 11-16 0z"/>
                    <path d="M12 2.252A8.014 8.014 0 0117.748 8H12V2.252z"/>
                  </svg>
                </div>
                <h2 className="text-2xl font-bold bg-gradient-to-r from-white to-zinc-300 bg-clip-text text-transparent">
                  {stockData.symbol}
                </h2>
              </div>
              <div className="flex items-center gap-2">
                <Chip 
                  color={getQualityColor(stockData.quality_score)} 
                  variant="shadow"
                  size="sm"
                  className="font-medium"
                >
                  Quality: {stockData.quality_score}/10
                </Chip>
                {stockData.overall_pattern_grade && (
                  <Chip 
                    color={getGradeColor(stockData.overall_pattern_grade)} 
                    variant="shadow"
                    size="sm"
                    className="font-medium"
                  >
                    Grade {stockData.overall_pattern_grade}
                  </Chip>
                )}
              </div>
            </div>
            <div className="text-right p-3 rounded-lg bg-gradient-to-br from-green-500/10 to-emerald-500/10 border border-green-500/20">
              <div className="text-xl font-bold text-green-400">
                {formatCurrency(stockData.entry_price || stockData.breakout_price)}
              </div>
              <div className="text-sm text-zinc-400">Entry Price</div>
            </div>
          </div>
        </ModalHeader>

        <ModalBody className="text-white modal-scrollbar">
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
            
            {/* Pattern Overview Card */}
            <Card className="bg-gradient-to-br from-zinc-800/60 to-zinc-900/60 backdrop-blur-sm border border-zinc-700/50 shadow-lg hover:shadow-xl hover:border-zinc-600/50 transition-all duration-300">
              <CardBody className="p-5">
                <h3 className="text-lg font-semibold mb-4 text-emerald-400 flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-emerald-500/20">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                  </div>
                  Pattern Overview
                </h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-zinc-300 text-sm">Duration:</span>
                    <span className="font-medium text-white">{stockData.pattern_duration_days} days</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-300 text-sm">Contractions:</span>
                    <span className="font-medium text-white">{stockData.num_contractions}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-300 text-sm">Compression:</span>
                    <span className="font-medium text-white">{formatNumber(stockData.compression_ratio, 3)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-300 text-sm">Pattern Range:</span>
                    <span className="font-medium text-white">{formatCurrency(stockData.pattern_low)} - {formatCurrency(stockData.pattern_high)}</span>
                  </div>
                </div>
              </CardBody>
            </Card>

            {/* Entry & Risk Management Card */}
            <Card className="bg-gradient-to-br from-zinc-800/60 to-zinc-900/60 backdrop-blur-sm border border-zinc-700/50 shadow-lg hover:shadow-xl hover:border-zinc-600/50 transition-all duration-300">
              <CardBody className="p-5">
                <h3 className="text-lg font-semibold mb-4 text-blue-400 flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-blue-500/20">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z"/>
                    </svg>
                  </div>
                  Risk Management
                </h3>
                <div className="space-y-3">
                  <div className="bg-green-500/10 rounded-lg p-2">
                    <div className="text-xs text-zinc-400">Entry Price</div>
                    <div className="text-lg font-bold text-green-400">{formatCurrency(stockData.entry_price)}</div>
                  </div>
                  <div className="bg-red-500/10 rounded-lg p-2">
                    <div className="text-xs text-zinc-400">Stop Loss</div>
                    <div className="text-lg font-bold text-red-400">{formatCurrency(stockData.suggested_stop_loss)}</div>
                  </div>
                  <div className="bg-emerald-500/10 rounded-lg p-2">
                    <div className="text-xs text-zinc-400">Take Profit</div>
                    <div className="text-lg font-bold text-emerald-400">{formatCurrency(stockData.suggested_take_profit)}</div>
                  </div>
                  <div className="text-center">
                    <span className="text-xs text-zinc-400">R:R Ratio </span>
                    <span className="font-bold text-white">1:{formatNumber(stockData.risk_reward_ratio, 2)}</span>
                  </div>
                </div>
              </CardBody>
            </Card>

            {/* Technical Indicators Card */}
            <Card className="bg-gradient-to-br from-zinc-800/60 to-zinc-900/60 backdrop-blur-sm border border-zinc-700/50 shadow-lg hover:shadow-xl hover:border-zinc-600/50 transition-all duration-300">
              <CardBody className="p-5">
                <h3 className="text-lg font-semibold mb-4 text-purple-400 flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-purple-500/20">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/>
                    </svg>
                  </div>
                  Technical Analysis
                </h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-zinc-300 text-sm">SMA 50:</span>
                    <span className="font-medium text-white">{formatCurrency(stockData.sma_50)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-300 text-sm">SMA 100:</span>
                    <span className="font-medium text-white">{formatCurrency(stockData.sma_100)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-300 text-sm">SMA 200:</span>
                    <span className="font-medium text-white">{formatCurrency(stockData.sma_200)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-300 text-sm">ATR:</span>
                    <span className="font-medium text-white">{formatCurrency(stockData.atr)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-300 text-sm">Prior Uptrend:</span>
                    <span className="font-medium text-white">{formatPercent(stockData.prior_uptrend_gain)}</span>
                  </div>
                  {/* Debug info - temporary */}
                  <div className="flex justify-between border-t border-zinc-700 pt-2 mt-2">
                    <span className="text-zinc-400 text-xs">Debug - Raw SMA Values:</span>
                    <span className="font-mono text-xs text-zinc-400">
                      50: {stockData.sma_50}, 100: {stockData.sma_100}, 200: {stockData.sma_200}
                    </span>
                  </div>
                </div>
              </CardBody>
            </Card>

            {/* Breakout Details Card */}
            <Card className="bg-gradient-to-br from-zinc-800/60 to-zinc-900/60 backdrop-blur-sm border border-zinc-700/50 shadow-lg hover:shadow-xl hover:border-zinc-600/50 transition-all duration-300">
              <CardBody className="p-5">
                <h3 className="text-lg font-semibold mb-4 text-orange-400 flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-orange-500/20">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z"/>
                    </svg>
                  </div>
                  Breakout Details
                </h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-zinc-300 text-sm">Breakout Date:</span>
                    <span className="font-medium text-white">{formatDate(stockData.breakout_date)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-300 text-sm">Breakout Price:</span>
                    <span className="font-medium text-white">{formatCurrency(stockData.breakout_price)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-300 text-sm">Breakout High:</span>
                    <span className="font-medium text-white">{formatCurrency(stockData.breakout_high)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-300 text-sm">Volume:</span>
                    <span className="font-medium text-white">{formatVolume(stockData.breakout_volume)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-300 text-sm">Strength:</span>
                    <span className="font-medium text-white">{formatPercent(stockData.breakout_strength)}</span>
                  </div>
                </div>
              </CardBody>
            </Card>

            {/* Quality Score Breakdown Card */}
            <Card className="bg-gradient-to-br from-zinc-800/60 to-zinc-900/60 backdrop-blur-sm border border-zinc-700/50 shadow-lg hover:shadow-xl hover:border-zinc-600/50 transition-all duration-300">
              <CardBody className="p-5">
                <h3 className="text-lg font-semibold mb-4 text-yellow-400 flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-yellow-500/20">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
                    </svg>
                  </div>
                  Quality Scores
                </h3>
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-zinc-300 text-sm">Duration</span>
                      <span className="font-medium text-white">{stockData.duration_score}/3</span>
                    </div>
                    <Progress 
                      value={(stockData.duration_score / 3) * 100} 
                      color={getScoreColor(stockData.duration_score, 3)}
                      size="sm"
                      className="w-full"
                    />
                  </div>
                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-zinc-300 text-sm">Contractions</span>
                      <span className="font-medium text-white">{stockData.contraction_score}/3</span>
                    </div>
                    <Progress 
                      value={(stockData.contraction_score / 3) * 100} 
                      color={getScoreColor(stockData.contraction_score, 3)}
                      size="sm"
                      className="w-full"
                    />
                  </div>
                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-zinc-300 text-sm">Compression</span>
                      <span className="font-medium text-white">{stockData.compression_score}/3</span>
                    </div>
                    <Progress 
                      value={(stockData.compression_score / 3) * 100} 
                      color={getScoreColor(stockData.compression_score, 3)}
                      size="sm"
                      className="w-full"
                    />
                  </div>
                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-zinc-300 text-sm">Volume</span>
                      <span className="font-medium text-white">{stockData.volume_score}/1</span>
                    </div>
                    <Progress 
                      value={(stockData.volume_score / 1) * 100} 
                      color={getScoreColor(stockData.volume_score, 1)}
                      size="sm"
                      className="w-full"
                    />
                  </div>
                </div>
              </CardBody>
            </Card>

            {/* Market Conditions Card */}
            <Card className="bg-gradient-to-br from-zinc-800/60 to-zinc-900/60 backdrop-blur-sm border border-zinc-700/50 shadow-lg hover:shadow-xl hover:border-zinc-600/50 transition-all duration-300">
              <CardBody className="p-5">
                <h3 className="text-lg font-semibold mb-4 text-cyan-400 flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-cyan-500/20">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd"/>
                    </svg>
                  </div>
                  Market Conditions
                </h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-zinc-300 text-sm">Above SMA 50:</span>
                    <Chip 
                      size="sm" 
                      color={stockData.above_sma50 ? "success" : "danger"}
                      variant="flat"
                    >
                      {stockData.above_sma50 ? "Yes" : "No"}
                    </Chip>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-300 text-sm">Above SMA 100:</span>
                    <Chip 
                      size="sm" 
                      color={stockData.above_sma100 ? "success" : "danger"}
                      variant="flat"
                    >
                      {stockData.above_sma100 ? "Yes" : "No"}
                    </Chip>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-300 text-sm">Price Breakout:</span>
                    <Chip 
                      size="sm" 
                      color={stockData.price_breakout ? "success" : "danger"}
                      variant="flat"
                    >
                      {stockData.price_breakout ? "Yes" : "No"}
                    </Chip>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-300 text-sm">Volume Surge:</span>
                    <Chip 
                      size="sm" 
                      color={stockData.volume_surge ? "success" : "danger"}
                      variant="flat"
                    >
                      {stockData.volume_surge ? "Yes" : "No"}
                    </Chip>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-300 text-sm">Green Candle:</span>
                    <Chip 
                      size="sm" 
                      color={stockData.green_breakout_candle ? "success" : "danger"}
                      variant="flat"
                    >
                      {stockData.green_breakout_candle ? "Yes" : "No"}
                    </Chip>
                  </div>
                </div>
              </CardBody>
            </Card>
          </div>

          {/* Contraction Details Section */}
          {contractionDetails.length > 0 && (
            <div className="mt-6">
              <h3 className="text-xl font-semibold mb-4 text-emerald-400 flex items-center gap-2">
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z"/>
                </svg>
                Contraction Details ({contractionDetails.length})
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {contractionDetails.map((contraction, index) => (
                  <Card key={`contraction-${index}-${contraction.contraction_number}`} className="bg-gradient-to-br from-zinc-800/60 to-zinc-900/60 backdrop-blur-sm border border-zinc-700/50 shadow-lg hover:shadow-xl hover:border-zinc-600/50 transition-all duration-300">
                    <CardBody className="p-4">
                      <div className="flex justify-between items-center mb-2">
                        <h4 className="font-semibold text-white">Contraction #{contraction.contraction_number}</h4>
                        <Chip size="sm" color="primary" variant="flat">
                          {contraction.length_days}d
                        </Chip>
                      </div>
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span className="text-zinc-300">Date:</span>
                          <span className="text-white">{formatDate(contraction.date)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-300">Price:</span>
                          <span className="text-white">{formatCurrency(contraction.price)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-300">Range:</span>
                          <span className="text-white">{formatCurrency(contraction.low)} - {formatCurrency(contraction.high)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-300">Range %:</span>
                          <span className="text-white">{formatPercent(contraction.range_pct)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-300">Volume:</span>
                          <span className="text-white">{formatVolume(contraction.volume)}</span>
                        </div>
                      </div>
                    </CardBody>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Weekly Breakdown Section */}
          {weeklyBreakdown.length > 0 && (
            <div className="mt-6">
              <h3 className="text-xl font-semibold mb-4 text-blue-400 flex items-center gap-2">
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd"/>
                </svg>
                Weekly Pattern Breakdown ({weeklyBreakdown.length} weeks)
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {weeklyBreakdown.map((week, index) => (
                  <Card key={`week-${index}-${week.week_end_date}`} className="bg-gradient-to-br from-zinc-800/60 to-zinc-900/60 backdrop-blur-sm border border-zinc-700/50 shadow-lg hover:shadow-xl hover:border-zinc-600/50 transition-all duration-300">
                    <CardBody className="p-4">
                      <div className="mb-2">
                        <h4 className="font-semibold text-white text-sm">Week {index + 1}</h4>
                        <p className="text-xs text-zinc-400">
                          {formatDate(week.week_start_date)} - {formatDate(week.week_end_date)}
                        </p>
                      </div>
                      <div className="space-y-1 text-xs">
                        <div className="flex justify-between">
                          <span className="text-zinc-300">Close:</span>
                          <span className="text-white font-medium">{formatCurrency(week.week_close)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-300">Range:</span>
                          <span className="text-white">{formatCurrency(week.week_low)} - {formatCurrency(week.week_high)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-300">Volume:</span>
                          <span className="text-white">{formatVolume(week.week_volume)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-300">Avg Vol:</span>
                          <span className="text-white">{formatVolume(week.week_avg_volume)}</span>
                        </div>
                      </div>
                    </CardBody>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Additional Metadata */}
          <div className="mt-6">
            <Card className="bg-gradient-to-br from-zinc-800/40 to-zinc-900/40 backdrop-blur-sm border border-zinc-700/50 shadow-lg hover:shadow-xl hover:border-zinc-600/50 transition-all duration-300">
              <CardBody className="p-4">
                <h3 className="text-lg font-semibold mb-3 text-zinc-300">Metadata</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div className="space-y-1">
                    <div className="flex justify-between">
                      <span className="text-zinc-400">Scan Date:</span>
                      <span className="text-white">{formatDate(stockData.scan_date)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-400">Pattern Start:</span>
                      <span className="text-white">{formatDate(stockData.pattern_start_date)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-400">Pattern End:</span>
                      <span className="text-white">{formatDate(stockData.pattern_end_date)}</span>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <div className="flex justify-between">
                      <span className="text-zinc-400">Instrument Token:</span>
                      <span className="text-white font-mono">{stockData.instrument_token}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-400">Run Time:</span>
                      <span className="text-white">{formatDate(stockData.run_time)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-400">Volume Surge Ratio:</span>
                      <span className="text-white">{formatNumber(stockData.volume_surge_ratio, 2)}x</span>
                    </div>
                  </div>
                </div>
              </CardBody>
            </Card>
          </div>
        </ModalBody>

        <ModalFooter className="border-t border-zinc-700/50 bg-gradient-to-r from-zinc-800/50 to-zinc-900/50 backdrop-blur-sm">
          <Button 
            color="default" 
            variant="ghost" 
            onPress={onClose}
            className="text-white hover:bg-zinc-700/50 border border-zinc-600/50 hover:border-zinc-500/50 transition-all duration-300 font-medium"
            size="md"
          >
            Close
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default StockDetailModal; 