import {useState} from 'react';
import {Container, TextField, Button, Typography, Box} from '@mui/material';
import {useNavigate} from 'react-router-dom';
import {toast} from 'react-toastify';
import './login.css'

function Login() {


    const [login, setLogin] = useState('');
    const [password, setPassword] = useState('');
    const navigate = useNavigate();

    const handleLogin = () => {
        // Проста імітація авторизації (заміни на реальний виклик API)
        if (login === 'admin' && password === 'password') {


            navigate('/home'); // Перенаправлення на домашню сторінку
            toast.success('Успішний вхід!');
        } else {
            toast.error('Невірний логін або пароль');
        }
    };

    return (
        <Container className="login-container">
            <Box className="login-form">
                <Typography variant="h4" gutterBottom>
                    Увійти
                </Typography>
                <Box sx={{display: 'flex', flexDirection: 'column', gap: 2}}>
                    <TextField
                        label="Логін"
                        value={login}
                        onChange={(e) => setLogin(e.target.value)}
                        fullWidth
                        variant="outlined"
                        className="text-field"
                    />
                    <TextField
                        label="Пароль"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        fullWidth
                        variant="outlined"
                        className="text-field"
                    />
                    <Button
                        variant="contained"
                        color="primary"
                        onClick={handleLogin}
                        fullWidth
                        className="login-button"
                    >
                        Увійти
                    </Button>
                </Box>
            </Box>
        </Container>
    );
}

export default Login;