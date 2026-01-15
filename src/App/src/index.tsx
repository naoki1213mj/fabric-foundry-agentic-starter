import { initializeIcons } from "@fluentui/react";
import ReactDOM from 'react-dom/client';
import { Provider } from 'react-redux';
import App from './App';
import './i18n'; // i18n 初期化
import './index.css';
import reportWebVitals from './reportWebVitals';
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

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
