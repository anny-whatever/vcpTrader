import api from './api.jsx';

// Risk scores API
export const calculateRiskScores = async (symbols) => {
  try {
    const symbolsParam = Array.isArray(symbols) ? symbols.join(',') : symbols;
    const response = await api.post('/api/risk_scores/risk/calculate', null, {
      params: { symbols: symbolsParam }
    });
    return response.data;
  } catch (error) {
    console.error('Error calculating risk scores:', error);
    throw error;
  }
};

export const getRiskScoresForSymbols = async (symbols) => {
  try {
    const symbolsParam = Array.isArray(symbols) ? symbols.join(',') : symbols;
    const response = await api.get('/api/risk_scores/risk/bulk', {
      params: { symbols: symbolsParam }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching risk scores:', error);
    throw error;
  }
};

export default api; 