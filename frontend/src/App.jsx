import { useState, useEffect } from 'react';
import { AppProvider } from './context/AppContext';
import ActivityBar from './components/Layout/ActivityBar';
import Sidebar from './components/Sidebar/Sidebar';
import EditorArea from './components/Editor/EditorArea';
import ChatPanel from './components/Chat/ChatPanel';
import StatusBar from './components/Layout/StatusBar';

function App() {
  const [showTerminal, setShowTerminal] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.ctrlKey && e.key === '`') {
        e.preventDefault();
        setShowTerminal(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <AppProvider>
      <div className="ide-container">
        <div className="ide-main">
          <ActivityBar />
          <Sidebar />
          <EditorArea
            showTerminal={showTerminal}
            onToggleTerminal={() => setShowTerminal(!showTerminal)}
          />
          <ChatPanel />
        </div>
        <StatusBar />
      </div>
    </AppProvider>
  );
}

export default App;
