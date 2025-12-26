import { Header, Sidebar, EditorPanel, AIPanel, Terminal } from './components/Layout';
import './App.css';

function App() {
    return (
        <div className="app">
            <Header />
            <main className="app-main">
                <Sidebar />
                <div className="workspace">
                    <EditorPanel />
                    <Terminal />
                </div>
                <AIPanel />
            </main>
        </div>
    );
}

export default App;
