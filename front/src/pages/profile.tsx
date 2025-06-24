import {useState, useEffect} from 'react';
import {Link} from 'react-router-dom';
import axios from 'axios';
import {Container, Typography, Box} from '@mui/material'; // Імпорт MUI компонентів
import './profile.css';

interface UserProfile {
    name: string;
    login: string;
}

const ProfilePage: React.FC = () => {
    const [user, setUser] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchUserProfile = async () => {
            const token = localStorage.getItem('access_token');
            if (!token) {
                setError("No token found in localStorage");
                setLoading(false);
                return;
            }

            try {
                const response = await axios.get(`http://127.0.0.1:8080/api/users/user`, {
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`,
                    },
                });

                if (!response.data) {
                    throw new Error('No data returned from API');
                }

                setUser(response.data);
            } catch (err) {
                setError(err instanceof Error ? err.message : "An error occurred");
            } finally {
                setLoading(false);
            }
        };

        fetchUserProfile();
    }, []);

    if (loading) return <div className="text-center py-4">Loading...</div>;
    if (error) return <div className="text-center py-4 text-red-500">{error}</div>;
    if (!user) return <div className="text-center py-4">No user data available</div>;

    return (
        <Container className="prof-home"
        >
            <Box className="navbar">
                <Typography className="logo">SOL-SPY-BOT</Typography>
                <Box className="nav-links">
                    <Link to="/settings">Налаштування</Link>
                    <Link to="/profile">Профіль</Link>
                    <Link to="/home">Головна</Link>
                </Box>
            </Box>
            <Box className="profile" sx={{p: 3, bgcolor: 'white', borderRadius: 2, boxShadow: 1, maxWidth:'100vw'}}>
                <Typography variant="h4" component="h1" gutterBottom sx={{fontWeight: 'bold', color: '#1976d2'}}>
                    User Profile
                </Typography>
                <Box sx={{spaceY: 2}}>
                    <Typography variant="body1" sx={{color: '#424242'}}>
                        <span style={{fontWeight: 'bold'}}>Username:</span> {user.name}
                    </Typography>
                    <Typography variant="body1" sx={{color: '#424242'}}>
                        <span style={{fontWeight: 'bold'}}>Email:</span> {user.login}
                    </Typography>
                </Box>
            </Box>
        </Container>
    );
};

export default ProfilePage;