import {BrowserRouter as Router, Route,Routes} from 'react-router-dom';

import 'react-toastify/dist/ReactToastify.css';
import Login from './pages/login.tsx';


function App() {


    return (
        <Router>
            <Routes>
                <Route path="/" element={<Login/>}/>
            </Routes>

        </Router>
    );
}

export default App;