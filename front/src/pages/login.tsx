import {useState} from 'react';
import {Container, TextField, Button, Typography, Box} from '@mui/material';
import {useNavigate} from 'react-router-dom';
import axios from "axios";
import {toast} from 'react-toastify';

import 'react-toastify/dist/ReactToastify.css'; // Імпорт стилів
import './login.css'

function Login() {


    const [login, setLogin] = useState('');
    const [password, setPassword] = useState('');
    const navigate = useNavigate();

    const handleLogin = async () => {
        try {

            const response = await axios.post('http://localhost:8080/api/users/login', {
                login: login,
                password: password,
            });

            const {access_token} = response.data;

            localStorage.setItem('access_token', access_token);


            toast.success('Успішний вхід!');


            navigate('/home');
        } catch (error) {
            if (axios.isAxiosError(error) && error.response) {

                toast.error(error.response.data.detail || 'Невірний логін або пароль');
            } else {

                toast.error('Помилка входу. Спробуйте ще раз.');
            }
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