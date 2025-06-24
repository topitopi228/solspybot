import {BrowserRouter as Router, Route, Routes} from 'react-router-dom';

import 'react-toastify/dist/ReactToastify.css';
import Login from './pages/login';
import HomePage from "./pages/home";
import BotManagementPage from "./pages/bot_management";
import WalletStatsPage from "./pages/wallet_stats";
import ProfilePage from "./pages/profile";

function App() {


    return (
        <Router>
            <Routes>
                <Route path="/" element={<Login/>}/>
                <Route path="/home" element={<HomePage/>}/>
                <Route path="/bot-management" element={<BotManagementPage/>}/>
                <Route path="/wallet-stats/:address" element={<WalletStatsPage/>}/>
                <Route path="/profile" element={<ProfilePage/>}/>
            </Routes>

        </Router>
    );
}

export default App;