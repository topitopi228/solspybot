import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import {
    Container,
    Typography,
    Box,
    Button,
    List,
    ListItem,
    ListItemText,
    ToggleButton,
    ToggleButtonGroup,
} from '@mui/material';
import {
    LineChart as RechartsLineChart,
    Line as RechartsLine,
    XAxis as RechartsXAxis,
    YAxis as RechartsYAxis,
    CartesianGrid as RechartsCartesianGrid,
    Tooltip as RechartsTooltip,
    Legend as RechartsLegend,
    ResponsiveContainer as RechartsResponsiveContainer,
} from 'recharts';
import './wallet_stats.css';

// Define the type for TrackedWalletTransaction
interface TrackedWalletTransaction {
    id: number;
    wallet_id: number;
    transaction_action: string | null;
    transaction_hash: string | null;
    status: string | null;
    token_address: string | null;
    token_symbol: string | null;
    buy_amount: number | null;
    sell_amount: number | null;
    transfer_amount: number | null;
    dex_name: string | null;
    price: number | null;
    timestamp: string | null;
}

// Define the type for TrackedStatisticsResponse
interface TrackedStatisticsResponse {
    id: number;
    tracked_wallet_id: number;
    deal_count: number | null;
    earned_sol: number | null;
    average_weekly_deals: number | null;
    net_sol_increase: number | null;
    created_at: string | null;
}

const WalletStatsPage: React.FC = () => {
    const { address } = useParams<{ address: string }>();
    const [stats, setStats] = useState<{
        balance: number;
        profit7Days: number;
        profit14Days: number;
        profit30Days: number;
        transactions: number;
        lastActivity: string;
    }>({
        balance: 0,
        profit7Days: 0,
        profit14Days: 0,
        profit30Days: 0,
        transactions: 0,
        lastActivity: 'Немає даних',
    });
    const [recentTransactions, setRecentTransactions] = useState<TrackedWalletTransaction[]>([]);
    const [timeInterval, setTimeInterval] = useState<'12h' | '24h' | '7d'>('24h');
    const [chartData, setChartData] = useState<any[]>([]);

    // Генеруємо фіксовані точки часу для осі X з округленням до повних годин
    const generateFixedTimePoints = (interval: '12h' | '24h' | '7d') => {
        const now = new Date();
        const points = [];
        const hours = interval === '12h' ? 12 : interval === '24h' ? 24 : 7;


        const roundedNow = new Date(now);
        roundedNow.setMinutes(0, 0, 0);

        if (interval === '7d') {
            for (let i = 0; i < hours; i++) {
                const date = new Date(roundedNow.getTime() - i * 24 * 60 * 60 * 1000);
                points.push(date.toLocaleDateString('uk-UA', { day: '2-digit', month: '2-digit' }));
            }
            return points.reverse();
        }

        for (let i = 0; i < hours; i++) {
            const time = new Date(roundedNow.getTime() - i * 60 * 60 * 1000);
            points.push(time.toLocaleTimeString('uk-UA', { hour: '2-digit', hour12: false }));
        }
        return points.reverse();
    };

    useEffect(() => {
        const fetchWalletStats = async () => {
            try {
                const accessToken = localStorage.getItem('access_token');
                if (!accessToken) {
                    console.error('No access token found in localStorage');
                    return;
                }


                const statsResponse = await axios.get(`http://127.0.0.1:8080/api/tracked-wallet/bot_tracking_wallets`, {
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${accessToken}`,
                    },
                });

                if (statsResponse.status === 200) {
                    const walletData = statsResponse.data.find(
                        (wallet: { wallet_address: string }) => wallet.wallet_address === address
                    );
                    if (walletData) {
                        setStats({
                            balance: walletData.sol_balance || 0,
                            profit7Days: walletData.profit_7_days || 0,
                            profit14Days: walletData.profit_14_days || 0,
                            profit30Days: walletData.profit_30_days || 0,
                            transactions: walletData.transaction_count || 0,
                            lastActivity: walletData.last_activity_at
                                ? new Date(walletData.last_activity_at).toLocaleString('uk-UA', {
                                      day: '2-digit',
                                      month: '2-digit',
                                      year: 'numeric',
                                      hour: '2-digit',
                                      minute: '2-digit',
                                      second: '2-digit',
                                  })
                                : 'Немає даних',
                        });
                    }
                }

                // Отримання транзакцій
                const transactionsResponse = await axios.get(
                    `http://127.0.0.1:8080/api/tracked-wallet/transaction/${address}`,
                    {
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${accessToken}`,
                        },
                    }
                );

                if (transactionsResponse.status === 200) {
                    const transactions = transactionsResponse.data.map((tx: TrackedWalletTransaction) => ({
                        id: tx.id,
                        wallet_id: tx.wallet_id,
                        transaction_action: tx.transaction_action || null,
                        transaction_hash: tx.transaction_hash || null,
                        status: tx.status || null,
                        token_address: tx.token_address || null,
                        token_symbol: tx.token_symbol || null,
                        buy_amount: tx.buy_amount || null,
                        sell_amount: tx.sell_amount || null,
                        transfer_amount: tx.transfer_amount || null,
                        dex_name: tx.dex_name || null,
                        price: tx.price || null,
                        timestamp: tx.timestamp
                            ? new Date(tx.timestamp).toLocaleString('uk-UA', {
                                  day: '2-digit',
                                  month: '2-digit',
                                  year: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit',
                                  second: '2-digit',
                              })
                            : null,
                    }));
                    setRecentTransactions(transactions);
                    setStats((prev) => ({
                        ...prev,
                        transactions: transactions.length,
                    }));
                }

                // Отримання статистики для графіка
                const statsEndpointResponse = await axios.get(
                    `http://127.0.0.1:8080/api/tracked-statistics/all/${address}`,
                    {
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${accessToken}`,
                        },
                    }
                );

                console.log('API Response:', statsEndpointResponse.data);

                if (statsEndpointResponse.status === 200) {
                    let statistics: TrackedStatisticsResponse[] = [];
                    if (Array.isArray(statsEndpointResponse.data)) {
                        statistics = statsEndpointResponse.data;
                    } else if (statsEndpointResponse.data[address]) {
                        statistics = statsEndpointResponse.data[address];
                    }

                    const rawChartData = statistics.map((stat) => ({
                        name: stat.created_at
                            ? new Date(stat.created_at).toLocaleTimeString('uk-UA', { hour: '2-digit', hour12: false })
                            : 'N/A',
                        count: stat.deal_count || 0,
                        profit: stat.earned_sol || 0,
                    })).filter((item) => item.name !== 'N/A');

                    // Генеруємо фіксовані точки часу
                    const fixedTimePoints = generateFixedTimePoints(timeInterval);
                    const interpolatedData = fixedTimePoints.map((time) => {
                        const dataPoint = rawChartData.find((d) => d.name === time);
                        return dataPoint || { name: time, count: 0, profit: 0 };
                    });

                    setChartData(interpolatedData);
                    console.log('Chart Data:', interpolatedData);
                }
            } catch (error) {
                console.error('Error fetching data:', error.response ? error.response.data : error.message);
            }
        };

        fetchWalletStats();
    }, [address, timeInterval]); // Додано timeInterval як залежність

    const handleIntervalChange = (event: React.MouseEvent<HTMLElement>, newInterval: '12h' | '24h' | '7d') => {
        if (newInterval) {
            setTimeInterval(newInterval);
            // Фільтрація та оновлення даних уже відбувається в useEffect через залежність timeInterval
        }
    };

    return (
        <Container className="wallet-stats-container">
            <Box className="navbar">
                <Typography className="logo">SOL-SPY-BOT</Typography>
                <Box className="nav-links">
                    <Link to="/settings">Налаштування</Link>
                    <Link to="/profile">Профіль</Link>
                    <Link to="/bot-management">Управління ботом</Link>
                </Box>
            </Box>

            <Box className="stats-content">
                <Typography variant="h4" gutterBottom>
                    Детальна статистика гаманця: {address}
                </Typography>
                <Box className="stats-layout">
                    <Box className="stats-period">
                        <Typography variant="h5" gutterBottom>
                            Статистика за періоди
                        </Typography>
                        <Box className="stats-card">
                            <Typography>Баланс: {stats.balance.toFixed(2)} SOL</Typography>
                            <Typography>Прибуток за 7 днів: {stats.profit7Days.toFixed(2)}%</Typography>
                            <Typography>Середня кількість угод за 7 днів: {stats.transactions}</Typography>
                            <Typography>Прибуток за 14 днів: {stats.profit14Days.toFixed(2)}%</Typography>
                            <Typography>Середня кількість угод за 14 днів: {stats.transactions}</Typography>
                            <Typography>Прибуток за 30 днів: {stats.profit30Days.toFixed(2)}%</Typography>
                            <Typography>Середня кількість угод за 30 днів: {stats.transactions}</Typography>
                            <Typography>Остання активність: {stats.lastActivity}</Typography>
                        </Box>
                    </Box>

                    <Box className="charts-section" sx={{ marginLeft: '80px' }}>
                        <Typography variant="h5" gutterBottom>
                            Графіки активності
                        </Typography>
                        <ToggleButtonGroup
                            value={timeInterval}
                            exclusive
                            onChange={handleIntervalChange}
                            aria-label="time interval"
                            sx={{ mb: 2, marginBottom: '40px' }}
                        >
                            <ToggleButton value="12h" aria-label="12 hours" sx={{ color: 'whitesmoke', fontWeight: 'bolder' }}>
                                12 годин
                            </ToggleButton>
                            <ToggleButton value="24h" aria-label="24 hours" sx={{ color: 'whitesmoke', fontWeight: 'bolder' }}>
                                24 години
                            </ToggleButton>
                            <ToggleButton value="7d" aria-label="7 days" sx={{ color: 'whitesmoke', fontWeight: 'bolder' }}>
                                7 днів
                            </ToggleButton>
                        </ToggleButtonGroup>

                        {/* Графік кількості угод */}
                        <Box sx={{ height: 400, mb: 4, minWidth: '60vw', maxWidth: '60vw', backgroundColor: '#1a2a44' }}>
                            <RechartsResponsiveContainer width="100%" height="100%">
                                <RechartsLineChart data={chartData}>
                                    <RechartsCartesianGrid strokeDasharray="3 3" stroke="#333" />
                                    <RechartsXAxis
                                        dataKey="name"
                                        stroke="whitesmoke"
                                        type="category"
                                        ticks={generateFixedTimePoints(timeInterval)}
                                    />
                                    <RechartsYAxis
                                        yAxisId="left"
                                        orientation="left"
                                        stroke="#8d31e2"
                                        style={{ fontSize: '18px' }}
                                        domain={[0, 'auto']}
                                    />
                                    <RechartsTooltip />
                                    <RechartsLegend />
                                    <RechartsLine
                                        yAxisId="left"
                                        type="monotone"
                                        dataKey="count"
                                        name="Кількість угод"
                                        stroke="#8d31e2"
                                        strokeWidth="3"
                                        dot={false}
                                    />
                                </RechartsLineChart>
                            </RechartsResponsiveContainer>
                        </Box>

                        {/* Графік прибутку */}
                        <Box sx={{ height: 400, mb: 4, minWidth: '60vw', minHeight: '40vh', backgroundColor: '#1a2a44' }}>
                            <RechartsResponsiveContainer width="100%" height="100%">
                                <RechartsLineChart data={chartData}>
                                    <RechartsCartesianGrid strokeDasharray="3 3" stroke="#333" />
                                    <RechartsXAxis
                                        dataKey="name"
                                        stroke="whitesmoke"
                                        type="category"
                                        ticks={generateFixedTimePoints(timeInterval)}
                                    />
                                    <RechartsYAxis
                                        yAxisId="left"
                                        orientation="left"
                                        stroke="#007c00"
                                        style={{ fontSize: '18px' }}
                                        domain={['auto', 'auto']}
                                        ticks={[-100, 0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]}
                                    />
                                    <RechartsTooltip formatter={(value) => `${value} SOL`} />
                                    <RechartsLegend />
                                    <RechartsLine
                                        yAxisId="left"
                                        type="monotone"
                                        dataKey="profit"
                                        name="Прибуток"
                                        stroke="#007c00"
                                        strokeWidth="3"
                                        dot={false}
                                    />
                                </RechartsLineChart>
                            </RechartsResponsiveContainer>
                        </Box>
                    </Box>

                    <Box className="transactions-section">
                        <Typography variant="h5" gutterBottom>
                            Останні транзакції
                        </Typography>
                        {recentTransactions.length === 0 ? (
                            <Typography>Немає транзакцій.</Typography>
                        ) : (
                            <List className="transactions-list">
                                {recentTransactions.map((tx) => (
                                    <ListItem key={tx.id} className="transaction-item">
                                        <ListItemText
                                            sx={{
                                                fontSize: '25px',
                                                fontWeight: 'bolder',
                                                color: tx.transaction_action === 'buy'
                                                    ? '#53af14'
                                                    : tx.transaction_action === 'sell'
                                                        ? 'red'
                                                        : tx.transaction_action === 'transfer'
                                                            ? 'gray'
                                                            : 'inherit',
                                                '& .MuiListItemText-secondary': {
                                                    color: 'whitesmoke',
                                                },
                                            }}
                                            primary={
                                                tx.transaction_action === 'transfer' && tx.transfer_amount !== null && tx.transfer_amount > 0
                                                    ? `${tx.transaction_action.toUpperCase() || 'Транзакція'}: ${tx.transfer_amount.toFixed(2)} ${tx.token_symbol || 'Unknown'}`
                                                    : (tx.transaction_action === 'buy' && tx.buy_amount !== null && tx.buy_amount > 0
                                                        ? `${tx.transaction_action.toUpperCase() || 'Купівля'}: ${tx.buy_amount.toFixed(2)} ${tx.token_symbol || 'Unknown'}`
                                                        : (tx.transaction_action === 'sell' && tx.sell_amount !== null && tx.sell_amount > 0
                                                            ? `${tx.transaction_action.toUpperCase() || 'Продаж'}: ${tx.sell_amount.toFixed(2)} ${tx.token_symbol || 'Unknown'}`
                                                            : 'Немає даних про кількість'))
                                            }
                                            secondary={
                                                `${tx.status ? tx.status : 'Невідомо'}, ${tx.timestamp || 'Немає даних'}, ${
                                                    tx.dex_name ? `${tx.dex_name}, ` : ''
                                                }${tx.transaction_hash ? `Hash: ${tx.transaction_hash}` : ''}`
                                            }
                                        />
                                    </ListItem>
                                ))}
                            </List>
                        )}
                    </Box>
                </Box>
                <Button
                    variant="contained"
                    color="secondary"
                    component={Link}
                    to="/bot-management"
                    sx={{ mt: 2, background: '#1e3c72', maxWidth: '50vw', marginLeft: '16vw' }}
                >
                    Повернутися
                </Button>
            </Box>
        </Container>
    );
};

export default WalletStatsPage;