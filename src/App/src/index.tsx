import { initializeIcons } from "@fluentui/react";
import ReactDOM from 'react-dom/client';
import { Provider } from 'react-redux';
import App from './App';
import './i18n'; // i18n 初期化
import './index.css';
import { store } from './store/store';

initializeIcons();

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <Provider store={store}>
    <App />
  </Provider>
);
