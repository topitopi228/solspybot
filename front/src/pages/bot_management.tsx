import {useState, useEffect} from 'react';
import {Link} from 'react-router-dom';
import DeleteIcon from '@mui/icons-material/Delete';
import StopIcon from '@mui/icons-material/Stop';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import axios from "axios";
import {
    Container,
    Typography,
    Box,
    Select,
    MenuItem,
    IconButton,
    FormControl,
    InputLabel,
    TextField,
    Button,
    List,
    ListItem,
    ListItemText,
} from '@mui/material';
import './bot_management.css';

const BotManagementPage: React.FC = () => {
    const [connectedWallets, setConnectedWallets] = useState<{
        address: string;
        blockchain: string;
        balance: number;
        status: boolean
    }[]>([]);
    const [viewedWallets, setViewedWallets] = useState<{
        id: number;
        botWalletId: number;
        address: string;
        followMode: 'monitor' | 'copy';
        isTracking: boolean;
        createdAt: Date;
        lastActivityAt: Date | null;
        solBalance: number | null;
    }[]>([]);
    const [trackingAddress, setTrackingAddress] = useState<string>('');
    const [trackedWallets, setTrackedWallets] = useState<string[]>([]);
    const [trackingModes, setTrackingModes] = useState<{ [key: string]: 'monitor' | 'copy' }>({}); // Індивідуальні режими для кожного гаманця
    const [walletStats, setWalletStats] = useState<{ [key: string]: { balance: number; profit: number } }>({});

    const handleDeleteWallet = async (address: string) => {
        try {
            const accessToken = localStorage.getItem('access_token');
            if (!accessToken) {
                console.error('No access token found in localStorage');
                return;
            }

            const response = await axios.delete(
                `http://127.0.0.1:8080/api/tracked-wallet/delete/${address}`,
                {
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${accessToken}`,
                    },
                }
            );

            if (response.status === 200) {

                setViewedWallets((prevWallets) => prevWallets.filter((wallet) => wallet.address !== address));
                console.log(`Гаманець ${address} успішно видалено`);
            } else {
                console.error('Не вдалося видалити гаманець:', response.data);
            }
        } catch (error) {
            console.error('Помилка при видаленні гаманця:', error.response ? error.response.data : error.message);
        }
    };

    // Функція для завантаження гаманців із бекенду
    const fetchUserWallets = async () => {
        try {
            const accessToken = localStorage.getItem('access_token');
            if (!accessToken) {
                console.error('No access token found in localStorage');
                return;
            }

            const response = await axios.get('http://127.0.0.1:8080/api/bot_wallets/user_wallets', {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`,
                },
            });

            if (response.status === 200) {
                // Перетворюємо token_address на address для сумісності з фронтендом
                const wallets = response.data.map((wallet: {
                    token_address: string;
                    balance: number;
                    status: boolean
                }) => ({
                    address: wallet.token_address,
                    blockchain: 'Solana', // За замовчуванням, якщо blockchain не повертається
                    balance: wallet.balance,
                    status: wallet.status,
                }));
                setConnectedWallets(wallets);
            } else {
                console.error('Failed to fetch wallets:', response.data);
            }
        } catch (error) {
            console.error('Error fetching user wallets:', error.response ? error.response.data : error.message);
        }
    };

    const fetchViewedWallets = async () => {
        try {
            const accessToken = localStorage.getItem('access_token');
            if (!accessToken) {
                console.error('No access token found in localStorage');
                return;
            }

            const response = await axios.get('http://127.0.0.1:8080/api/tracked-wallet/bot_tracking_wallets', {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`,
                },
            });

            console.log(response.data)

            if (response.status === 200) {
                const wallets = response.data.map((wallet: {
                    id: number;
                    bot_wallet_id: number;
                    wallet_address: string;
                    follow_mode: string;
                    copy_mode: string;
                    is_tracking: boolean;
                    created_at: string;
                    last_activity_at: string | null;
                    sol_balance: number | null;
                }) => ({
                    id: wallet.id,
                    botWalletId: wallet.bot_wallet_id,
                    address: wallet.wallet_address,
                    followMode: wallet.follow_mode as 'monitor' | 'coppy' ? null : null, // Перетворюємо у нижній регістр для сумісності
                    copy_mode: wallet.copy_mode as 'copy_percent'|'copy_xpercent'|'copy_fix' ? null : null,
                    isTracking: wallet.is_tracking,
                    createdAt: new Date(wallet.created_at),
                    lastActivityAt: wallet.last_activity_at ? new Date(wallet.last_activity_at) : null,
                    solBalance: wallet.sol_balance,
                }));
                console.log('Mapped wallets:', wallets);
                setViewedWallets(wallets);
            } else {
                console.error('Failed to fetch viewed wallets:', response.data);
            }
        } catch (error) {
            console.error('Error fetching viewed wallets:', error.response ? error.response.data : error.message);
        }
    };
    const handleStopTracking = async (walletAddress: string) => {
        try {
            const accessToken = localStorage.getItem('access_token');
            if (!accessToken) {
                console.error('No access token found in localStorage');
                return;
            }

            const response = await axios.put(
                `http://127.0.0.1:8080/api/tracked-wallet/stop-tracking/${walletAddress}`,
                {},
                {
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${accessToken}`,
                    },
                }
            );

            if (response.status === 200) {

                setViewedWallets((prevWallets) =>
                    prevWallets.map((wallet) =>
                        wallet.address === walletAddress
                            ? {...wallet, isTracking: false, followMode: null}
                            : wallet
                    )
                );
                console.log(`Відстежування гаманця ${walletAddress} припинено`);
            } else {
                console.error('Не вдалося припинити відстежування:', response.data);
            }
        } catch (error) {
            console.error('Помилка при припиненні відстежування:', error.response ? error.response.data : error.message);
        }
    }

    const handleStartTracking = async (walletAddress: string) => {
        try {
            const accessToken = localStorage.getItem('access_token');
            if (!accessToken) {
                console.error('No access token found in localStorage');
                return;
            }

            const response = await axios.put(
                `http://127.0.0.1:8080/api/tracked-wallet/start-tracking/${walletAddress}`,
                {},
                {
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${accessToken}`,
                    },
                }
            );

            if (response.status === 200) {
                // Оновлюємо локальний стан після успішного першого запиту
                setViewedWallets((prevWallets) =>
                    prevWallets.map((wallet) =>
                        wallet.address === walletAddress
                            ? {...wallet, isTracking: true, followMode: 'monitor'}
                            : wallet
                    )
                );
                console.log(`Відстежування гаманця ${walletAddress} розпочато (після PUT)`);

                // Другий запит: POST /api/copy_trading/start-tracking/ виконуємо у фоновому режимі
                const requestData = {
                    wallet_address: walletAddress,
                    interval_seconds: 5, // Значення за замовчуванням
                };

                axios.post(
                    `http://127.0.0.1:8080/api/copy_trading/start-tracking/`,
                    requestData,
                    {
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${accessToken}`,
                        },
                    }
                ).then(
                    (postResponse) => {
                        if (postResponse.status === 200) {
                            console.log(`Другий запит (POST) для ${walletAddress} успішно відправлено`);
                        } else {
                            console.error('Помилка у другому запиті (POST):', postResponse.data);
                        }
                    }
                ).catch((error) => {
                    console.error('Помилка при відправленні другого запиту (POST):', error.message);
                });
            } else {
                console.error('Не вдалося розпочати відстежування (PUT):', response.data);
            }
        } catch (error) {
            console.error('Помилка при початку відстежування:', error.response ? error.response.data : error.message);
        }
    };

    const handleAddTracking = async () => {
        if (trackingAddress && !trackedWallets.includes(trackingAddress)) {
            try {
                const accessToken = localStorage.getItem('access_token');
                if (!accessToken) {
                    console.error('No access token found in localStorage');
                    return;
                }

                // Формуємо об’єкт для відправки на бекенд
                const requestData = {
                    wallet_address: trackingAddress,
                };

                // Відправляємо POST-запит на бекенд
                const response = await axios.post('http://127.0.0.1:8080/api/tracked-wallet/', requestData, {
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${accessToken}`,
                    },
                });

                if (response.status === 201 || response.data !== null) {
                    // Якщо запит успішний, оновлюємо локальний стан
                    setTrackedWallets([...trackedWallets, trackingAddress]);
                    setTrackingModes({...trackingModes, [trackingAddress]: 'monitor'}); // За замовчуванням просте відстеження
                    setTrackingAddress('');
                    console.log('Гаманець успішно додано для відстежування:', trackingAddress);
                } else {
                    console.error('Не вдалося додати гаманець:', response.data);
                }
            } catch (error) {
                console.error('Помилка при додаванні гаманця:', error.response ? error.response.data : error.message);
            }
        }
    };


    useEffect(() => {
        fetchUserWallets();
        fetchViewedWallets();
        const interval = setInterval(() => {
            setWalletStats((prev) => {
                const newStats = {...prev};
                trackedWallets.forEach((wallet) => {
                    if (!newStats[wallet]) newStats[wallet] = {balance: 0, profit: 0};
                    newStats[wallet] = {
                        balance: newStats[wallet].balance + (Math.random() - 0.5) * 10,
                        profit: newStats[wallet].profit + (Math.random() - 0.5) * 2,
                    };
                });
                return newStats;
            });
        }, 2000);
        return () => clearInterval(interval);
    }, [trackedWallets]);


    const handleRemoveTracking = (address: string) => {
        const newTrackedWallets = trackedWallets.filter((w) => w !== address);
        setTrackedWallets(newTrackedWallets);
        const newTrackingModes = {...trackingModes};
        delete newTrackingModes[address];
        setTrackingModes(newTrackingModes);
    };

    const handleFollowModeChange = async (walletAddress: string, newMode: 'monitor' | 'copy') => {
        try {
            const accessToken = localStorage.getItem('access_token');
            if (!accessToken) {
                console.error('No access token found in localStorage');
                return;
            }

            const requestData = {
                follow_mode: newMode,
                wallet_address: walletAddress,
            };

            const response = await axios.put(`http://127.0.0.1:8080/api/tracked-wallet/status`, requestData, {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`,
                },
            });

            if (response.status === 201 || response.status == 200) {
                setViewedWallets((prev) =>
                    prev.map((wallet) =>
                        wallet.address === walletAddress ? {...wallet, followMode: newMode} : wallet
                    )
                );
                console.log(`Режим для гаманця ${walletAddress} змінено на ${newMode}`);
            } else {
                console.error('Не вдалося оновити режим:', response.data);
            }
        } catch (error) {
            console.error('Помилка при оновленні режиму:', error.response ? error.response.data : error.message);
        }
    };

    return (
        <Container className="bot-management-container" disableGutters maxWidth={false}>
            {/* Навігаційна панель */}
            <Box className="navbar">
                <Typography className="logo">SOL-SPY-BOT</Typography>
                <Box className="nav-links">
                    <Link to="/settings">Налаштування</Link>
                    <Link to="/profile">Профіль</Link>
                    <Link to="/home">Головна</Link>
                </Box>
            </Box>

            {/* Основний контент */}
            <Box className="main-content">
                {/* Ліва частина: Управління ботом і додавання гаманців */}
                <Box className="management-section">
                    <Typography variant="h4" gutterBottom>
                        Управління ботом
                    </Typography>

                    {/* Список підключених гаманців */}
                    <Box className="wallet-list">
                        <Typography variant="h6">Підключені гаманці:</Typography>
                        {connectedWallets.length === 0 ? (
                            <Typography>Немає підключених гаманців.</Typography>
                        ) : (
                            <List>
                                {connectedWallets.map((wallet) => (

                                    <ListItem key={wallet.address}>
                                        <ListItemText
                                            primary={`${wallet.address} (${wallet.blockchain})`}
                                            secondary={
                                                <Box component="span">
                                                    <Typography variant="body2" component="span" sx={{fontSize: '22px'}}>
                                                        Баланс: {(wallet.balance != null ? wallet.balance.toFixed(2) : '0.00')} SOL
                                                    </Typography>
                                                    <br/>
                                                    <Typography
                                                        variant="body2"
                                                        component="span"
                                                        sx={{
                                                            color: wallet.status ? '#2E7D32' : '#B8860B', // Темно-зелений для "Активний", темно-жовтий для "Неактивний"
                                                            fontSize: '22px', // Збільшуємо розмір тексту в 2 рази (з 0.875rem до 1.75rem)
                                                        }}
                                                    >
                                                        Статус: {wallet.status ? 'Активний' : 'Неактивний'}
                                                    </Typography>
                                                </Box>
                                            }
                                        />
                                    </ListItem>

                                ))}
                            </List>
                        )}
                        {connectedWallets.some((wallet) => wallet.status) && (
                            <Typography variant="h5" color="#172b4e" sx={{mt: 2,color:"white",fontWeight: "bolder",fontSize:"30px",marginBottom:"40px"}}>
                                Бот управляє гаманцем:{' '}
                                {connectedWallets.find((wallet) => wallet.status)?.address || 'Немає активного гаманця'}
                            </Typography>
                        )}
                    </Box>

                    {/* Вибір адреси для відстежування */}
                    <Box className="tracking-section">
                        <Typography variant="h6">Додати гаманець для відстежування:</Typography>
                        <Box sx={{display: 'flex', gap: 1, mb: 2}}>
                            <TextField
                                label="Адреса гаманця"
                                value={trackingAddress}
                                onChange={(e) => setTrackingAddress(e.target.value)}
                                fullWidth
                                variant="outlined"
                            />
                            <Button variant="contained" color="primary" onClick={handleAddTracking}>
                                Додати
                            </Button>
                        </Box>

                        <Typography variant="h6">Відстежувані і раніше відстежувані гаманці:</Typography>
                        <List>
                            {viewedWallets.length === 0 ? (
                                <Typography>Немає відстежуваних гаманців.</Typography>
                            ) : (
                                viewedWallets.map((wallet) => (
                                    <ListItem key={wallet.id} sx={{display: 'flex', alignItems: 'center', gap: 1}}>
                                        <ListItemText primary={`${wallet.address} (ID: ${wallet.id})`}/>
                                        <FormControl sx={{minWidth: 200}}>
                                            <InputLabel id={`follow-mode-label-${wallet.id}`}>Режим
                                                відстежування</InputLabel>
                                            <Select
                                                labelId={`follow-mode-label-${wallet.id}`}
                                                value={wallet.isTracking ? wallet.followMode || 'monitor' : ''}
                                                onChange={(e) => handleFollowModeChange(wallet.address, e.target.value as 'monitor' | 'copy')}
                                                label="Режим відстежування"
                                                disabled={!wallet.isTracking}
                                            >
                                                <MenuItem value="monitor">Монітор</MenuItem>
                                                <MenuItem value="copy">Копія</MenuItem>
                                            </Select>
                                        </FormControl>
                                        {wallet.isTracking ? (
                                            <IconButton
                                                sx={{background:"#172b4e"}}
                                                edge="end"
                                                aria-label="stop-tracking"
                                                onClick={() => handleStopTracking(wallet.address)}
                                                color="warning"
                                            >
                                                <StopIcon/>
                                            </IconButton>
                                        ) : (
                                            <IconButton
                                                edge="end"
                                                aria-label="start-tracking"
                                                onClick={() => handleStartTracking(wallet.address)}
                                                color="success"
                                            >
                                                <PlayArrowIcon/>
                                            </IconButton>
                                        )}
                                        <IconButton
                                            edge="end"
                                            aria-label="delete"
                                            onClick={() => handleDeleteWallet(wallet.address)}
                                            color="error"
                                        >
                                            <DeleteIcon/>
                                        </IconButton>
                                    </ListItem>
                                ))
                            )}
                        </List>
                    </Box>
                </Box>

                {/* Права частина: Статистика гаманців */}
                <Box className="stats-section">
                    <Typography variant="h4" gutterBottom>
                        Статистика гаманців
                    </Typography>
                    {viewedWallets.length === 0 ? (
                        <Typography>Немає гаманців для відстежування.</Typography>
                    ) : (
                        viewedWallets.map((wallet) => (
                            <Box key={wallet.id} className="stats-card" sx={{mb: 2}}>
                                <Typography variant="h6">{`${wallet.address} (ID: ${wallet.id})`}</Typography>
                                <Typography>Баланс: {(wallet.solBalance || 0).toFixed(2)} SOL</Typography>
                                <Typography>
                                    Режим: {wallet.followMode === 'monitor'
                                    ? 'Моніторинг'
                                    : wallet.followMode === 'copy'
                                        ? 'Копіювання транзакцій'
                                        : 'Гаманець не відстежується'}
                                </Typography>
                                <Typography>Створено: {wallet.createdAt.toLocaleDateString()}</Typography>
                                {wallet.lastActivityAt && (
                                    <Typography>Остання
                                        активність: {wallet.lastActivityAt.toLocaleDateString()}</Typography>
                                )}
                                <Button
                                    variant="contained"
                                    color="primary"
                                    sx={{mt: 1}}
                                    component={Link}
                                    to={`/wallet-stats/${wallet.address}`}
                                >
                                    Детальніша статистика
                                </Button>
                            </Box>
                        ))
                    )}
                </Box>
            </Box>
        </Container>
    );
};

export default BotManagementPage;