// src/pages/Home.tsx
import {useState} from 'react';
import {Link} from 'react-router-dom';
import {
    Container,
    Typography,
    Box,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    TextField,
    Button,
} from '@mui/material';
import './Home.css';
import axios from "axios";

const HomePage: React.FC = () => {
    const [blockchain, setBlockchain] = useState<string>('Solana');
    const [walletAddress, setWalletAddress] = useState<string>('');
    const [privateKey, setPrivateKey] = useState<string>('');
    const [isWalletConnected, setIsWalletConnected] = useState<boolean>(false);

    const handleConnect = async () => {
        if (!walletAddress || !privateKey) {
            console.log('Please fill in all fields');
            return;
        }
        console.log('Connecting wallet:', {blockchain, walletAddress, privateKey});

        // Отримання токена з localStorage
        const accessToken = localStorage.getItem('access_token');
        if (!accessToken) {
            console.log('No access token found in localStorage');
            return;
        }

        // Підготовка даних для запиту
        const requestData = {
            token_address: walletAddress, // Використовуємо walletAddress як token_address
            private_key: privateKey,
            status: true,
        };

        try {
            const response = await axios.post('http://127.0.0.1:8080/api/bot_wallets/add-wallet-for-bot', requestData, {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`,
                },
            });

            if (response.status === 200) {
                const result = response.data;
                console.log('Wallet added successfully:', result);
                setIsWalletConnected(true);
            } else {
                console.log('Error adding wallet:', response.data);
            }
        } catch (error) {
            console.error('Network error:', error);
            if (error.response) {
                console.log('Server error:', error.response.data);
            }
        }
    };

    const handleDisconnect = () => {
        setIsWalletConnected(false); // Гаманець відключений
        setBlockchain('Solana'); // Скидаємо вибір блокчейну
        setWalletAddress(''); // Очищаємо адресу
        setPrivateKey(''); // Очищаємо приватний ключ
    };

    return (
        <Container className="home-container" disableGutters maxWidth={false}>
            {/* Навігаційна панель */}
            <Box className="navbar">
                <Typography className="logo">SOL-SPY-BOT</Typography>
                <Box className="nav-links">
                    <Link to="/settings">Налаштування</Link>
                    <Link to="/profile">Профіль</Link>
                    <Link to="/bot-management">Bot Управління</Link>
                </Box>
            </Box>

            {/* Секція підключення гаманця */}
            <Box component="section" className="section">
                <Typography variant="h4" gutterBottom>
                    Підключення гаманця
                </Typography>
                <Box className="wallet-connect">
                    <FormControl fullWidth>
                        <InputLabel>Блокчейн</InputLabel>
                        <Select
                            value={blockchain}
                            onChange={(e) => setBlockchain(e.target.value as string)}
                            label="Блокчейн"
                            disabled={isWalletConnected} // Деактивуємо вибір, якщо гаманець підключений
                        >
                            <MenuItem value="Solana">Solana</MenuItem>
                            <MenuItem value="Ethereum">Ethereum</MenuItem>
                            <MenuItem value="Binance">Binance Smart Chain</MenuItem>
                        </Select>
                    </FormControl>
                    <TextField
                        label="Адреса гаманця"
                        value={walletAddress}
                        onChange={(e) => setWalletAddress(e.target.value)}
                        fullWidth
                        variant="outlined"
                        InputProps={{style: {backgroundColor: '#2a5298', color: '#fff'}}}
                        InputLabelProps={{style: {color: '#aaa'}}}
                        disabled={isWalletConnected} // Деактивуємо поле, якщо гаманець підключений
                    />
                    <TextField
                        label="Приватний ключ"
                        type="password"
                        value={privateKey}
                        onChange={(e) => setPrivateKey(e.target.value)}
                        fullWidth
                        variant="outlined"
                        InputProps={{style: {backgroundColor: '#2a5298', color: '#fff'}}}
                        InputLabelProps={{style: {color: '#aaa'}}}
                        disabled={isWalletConnected} // Деактивуємо поле, якщо гаманець підключений
                    />
                    {isWalletConnected ? (
                        <Button
                            variant="contained"
                            color="secondary"
                            onClick={handleDisconnect}
                            fullWidth
                        >
                            Відключити
                        </Button>
                    ) : (
                        <Button variant="contained" color="primary" onClick={handleConnect} fullWidth>
                            Підключити
                        </Button>
                    )}
                </Box>
                <Typography variant="caption" className="warning">
                    Увага: Ніколи не діліться приватним ключем крім цього бота і себе!
                </Typography>
            </Box>

            {/* Статистика гаманця */}
            <Box component="section" className="section">
                <Typography variant="h4" gutterBottom>
                    Статистика гаманця
                </Typography>
                <Box className="stats-card">
                    <Typography>Баланс: 100 SOL</Typography>
                    <Typography>Прибуток: +10% за місяць</Typography>
                </Box>
            </Box>
        </Container>
    );
};

export default HomePage;