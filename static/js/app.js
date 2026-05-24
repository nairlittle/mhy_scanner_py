// MHY Scanner WebUI - 主逻辑

const API = {
    async get(url) {
        const r = await fetch(url);
        return r.json();
    },
    async post(url, data) {
        const r = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return r.json();
    },
    async put(url, data) {
        const r = await fetch(url, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return r.json();
    },
    async del(url) {
        const r = await fetch(url, { method: 'DELETE' });
        return r.json();
    }
};

// Toast 通知
function toast(msg, type = 'info') {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.className = `toast ${type} show`;
    clearTimeout(el._timeout);
    el._timeout = setTimeout(() => el.classList.remove('show'), 2500);
}

// ============ 导航 ============
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        item.classList.add('active');
        
        const page = item.dataset.page;
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById('page-' + page).classList.add('active');
        
        // 加载对应页面数据
        if (page === 'accounts') loadAccounts();
        if (page === 'screen') { loadAccountSelects(); loadLastSettings('screen'); }
        if (page === 'live') { loadAccountSelects(); loadLastSettings('live'); }
        if (page === 'settings') loadSettings();
    });
});

// ============ 登录标签切换 ============
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
        
        // 切换到二维码时停止其他操作
        if (btn.dataset.tab === 'qrcode') {
            stopQRPolling();
        }
    });
});

// ============ 二维码登录 ============
let qrPollTimer = null;
let qrCodeInstance = null;

document.getElementById('startQRCodeBtn').addEventListener('click', startQRCodeLogin);
document.getElementById('qrcodeRefreshBtn').addEventListener('click', startQRCodeLogin);

async function startQRCodeLogin() {
    stopQRPolling();
    if (qrCodeInstance) {
        qrCodeInstance.clear();
        qrCodeInstance = null;
    }
    const placeholder = document.getElementById('qrcodePlaceholder');
    const refreshBtn = document.getElementById('qrcodeRefreshBtn');
    const status = document.getElementById('qrcodeStatus');
    const qrBox = document.getElementById('qrcodeBox');
    
    refreshBtn.style.display = 'none';
    placeholder.style.display = 'flex';
    placeholder.textContent = '获取中...';
    status.textContent = '';
    
    // 清除旧的二维码canvas
    qrBox.querySelectorAll('canvas').forEach(c => c.remove());
    
    try {
        const r = await API.get('/api/auth/qrcode');
        if (r.url) {
            qrCodeInstance = new QRCode(qrBox, {
                text: r.url,
                width: 200,
                height: 200,
                colorDark: '#000000',
                colorLight: '#ffffff',
            });
            placeholder.style.display = 'none';
            status.textContent = '请使用米游社APP扫码';
            
            qrPollTimer = setInterval(() => pollQRState(r.ticket), 1000);
        } else {
            placeholder.textContent = '获取失败，请重试';
        }
    } catch (e) {
        placeholder.textContent = '网络错误，请重试';
    }
}

async function pollQRState(ticket) {
    try {
        const r = await API.get('/api/auth/qrcode/state/' + ticket);
        const status = document.getElementById('qrcodeStatus');
        
        if (r.stat === 'Scanned') {
            status.textContent = '已扫码，请在手机上点击确认登录';
            status.style.color = '#2563eb';
        } else if (r.stat === 'Confirmed') {
            stopQRPolling();
            status.textContent = '登录成功，正在保存...';
            status.style.color = '#22c55e';
            
            // 完成登录保存账号
            const loginR = await API.post(`/api/auth/qrcode/login?ticket=${ticket}&uid=${r.uid}&game_token=${r.game_token}`);
            if (loginR.retcode === 0) {
                toast('登录成功！账号已保存', 'success');
                status.textContent = '登录成功！';
                document.getElementById('qrcodeRefreshBtn').style.display = 'flex';
            } else {
                toast('获取SToken失败', 'error');
                status.textContent = '登录失败：' + (loginR.message || '未知错误');
                status.style.color = '#ef4444';
            }
        } else if (r.stat === 'Expired') {
            stopQRPolling();
            status.textContent = '二维码已过期';
            status.style.color = '#ef4444';
            document.getElementById('qrcodeRefreshBtn').style.display = 'flex';
        }
    } catch (e) {
        // ignore
    }
}

function stopQRPolling() {
    if (qrPollTimer) {
        clearInterval(qrPollTimer);
        qrPollTimer = null;
    }
}

// ============ 短信登录 ============
const smsMobile = document.getElementById('smsMobile');
let smsActionType = '';
let geetestCaptchaObj = null;

smsMobile.addEventListener('input', () => {
    document.getElementById('smsSendBtn').disabled = smsMobile.value.length < 11;
});

// 极验验证码
function showGeeTest(gt, challenge) {
    return new Promise((resolve, reject) => {
        document.getElementById('geetestModal').style.display = 'flex';
        document.getElementById('geetestContainer').innerHTML = '';

        if (typeof initGeetest4 === 'undefined') {
            closeGeeTest();
            reject(new Error('极验SDK加载失败'));
            return;
        }

        initGeetest4({
            captchaId: gt,
            product: 'bind',
            riskType: 'slide',
            nextWidth: '260px'
        }, function (obj) {
            geetestCaptchaObj = obj;
            obj.appendTo('#geetestContainer');
            obj.onSuccess(function () {
                const result = obj.getValidate();
                closeGeeTest();
                resolve({
                    challenge: challenge,
                    validate: JSON.stringify(result),
                    seccode: JSON.stringify(result)
                });
            });
            obj.onClose(function () {
                closeGeeTest();
                reject(new Error('用户取消验证'));
            });
            obj.onError(function (e) {
                closeGeeTest();
                reject(new Error('验证出错: ' + (e.msg || '')));
            });
        });
    });
}

function closeGeeTest() {
    document.getElementById('geetestModal').style.display = 'none';
    document.getElementById('geetestContainer').innerHTML = '';
    if (geetestCaptchaObj) {
        try { geetestCaptchaObj.destroy(); } catch (e) {}
        geetestCaptchaObj = null;
    }
}

document.getElementById('smsSendBtn').addEventListener('click', async () => {
    const mobile = smsMobile.value.trim();
    if (!/^1[3-9]\d{9}$/.test(mobile)) {
        toast('请输入正确的手机号', 'error');
        return;
    }
    
    const btn = document.getElementById('smsSendBtn');
    btn.disabled = true;
    btn.textContent = '发送中...';
    
    try {
        // 首次请求 - 获取GeeTest参数
        let r = await API.post('/api/auth/sms/send', { mobile });
        
        // 如果需要极验验证
        if (r.mmt_type === 5 || r.action_type) {
            smsActionType = r.action_type || '';
            try {
                const geeResult = await showGeeTest(r.gt, r.challenge);
                r = await API.post('/api/auth/sms/send', {
                    mobile,
                    aigis: geeResult.validate
                });
            } catch (e) {
                btn.disabled = false;
                btn.textContent = '发送验证码';
                toast(e.message || '验证取消', 'info');
                return;
            }
        }

        if (r.retcode === 0) {
            toast('验证码已发送', 'success');
            startSMSTimer();
        } else if (r.retcode === -3006) {
            toast('请求过于频繁，请稍后再试', 'error');
            btn.disabled = false;
            btn.textContent = '发送验证码';
        } else {
            toast(r.message || '发送失败', 'error');
            btn.disabled = false;
            btn.textContent = '发送验证码';
        }
    } catch (e) {
        toast('网络错误', 'error');
        btn.disabled = false;
        btn.textContent = '发送验证码';
    }
});

function startSMSTimer() {
    const btn = document.getElementById('smsSendBtn');
    let sec = 60;
    btn.textContent = `${sec}秒`;
    const timer = document.getElementById('smsTimer');
    timer.textContent = `${sec}秒后可重新发送`;
    
    const interval = setInterval(() => {
        sec--;
        if (sec <= 0) {
            clearInterval(interval);
            timer.textContent = '';
            btn.disabled = false;
            btn.textContent = '发送验证码';
        } else {
            btn.textContent = `${sec}秒`;
            timer.textContent = `${sec}秒后可重新发送`;
        }
    }, 1000);
}

document.getElementById('smsLoginBtn').addEventListener('click', async () => {
    const mobile = smsMobile.value.trim();
    const captcha = document.getElementById('smsCode').value.trim();
    
    if (!mobile || !captcha) {
        toast('请填写手机号和验证码', 'error');
        return;
    }
    
    try {
        const r = await API.post('/api/auth/sms/login', {
            mobile,
            captcha,
            action_type: smsActionType,
            gt: '',
            challenge: '',
            gee_validate: ''
        });
        
        if (r.retcode === 0) {
            toast('登录成功！账号已保存', 'success');
            smsMobile.value = '';
            document.getElementById('smsCode').value = '';
            smsActionType = '';
        } else if (r.retcode === -3200) {
            if (r.data && r.data.gt) {
                try {
                    const geeResult = await showGeeTest(r.data.gt, r.data.challenge);
                    const r2 = await API.post('/api/auth/sms/login', {
                        mobile,
                        captcha,
                        action_type: smsActionType,
                        gt: r.data.gt,
                        challenge: r.data.challenge,
                        gee_validate: geeResult.validate
                    });
                    if (r2.retcode === 0) {
                        toast('登录成功！账号已保存', 'success');
                        smsMobile.value = '';
                        document.getElementById('smsCode').value = '';
                        smsActionType = '';
                    } else {
                        toast(r2.message || '登录失败', 'error');
                    }
                } catch (e) {
                    toast('验证取消', 'info');
                }
            } else {
                toast(r.message || '登录失败', 'error');
            }
        } else {
            toast(r.message || '登录失败', 'error');
        }
    } catch (e) {
        toast('网络错误', 'error');
    }
});

// ============ Cookie登录 ============
document.getElementById('cookieLoginBtn').addEventListener('click', async () => {
    const cookie = document.getElementById('cookieInput').value.trim();
    const note = document.getElementById('cookieNote').value.trim();
    
    if (!cookie) {
        toast('请粘贴Cookie', 'error');
        return;
    }
    
    try {
        const r = await API.post('/api/auth/cookie/login', { cookie, note });
        if (r.retcode === 0) {
            toast('登录成功！', 'success');
            document.getElementById('cookieInput').value = '';
            document.getElementById('cookieNote').value = '';
        } else {
            toast(r.message || '登录失败', 'error');
        }
    } catch (e) {
        toast('网络错误', 'error');
    }
});

// ============ 崩坏3 B服登录 ============
document.getElementById('bh3LoginBtn').addEventListener('click', async () => {
    const account = document.getElementById('bh3Account').value.trim();
    const password = document.getElementById('bh3Password').value.trim();
    
    if (!account || !password) {
        toast('请填写账号和密码', 'error');
        return;
    }
    
    const btn = document.getElementById('bh3LoginBtn');
    btn.disabled = true;
    btn.textContent = '登录中...';
    
    try {
        const capR = await API.get('/api/auth/bh3_bili/captcha');
        if (capR.retcode !== 0) {
            toast('获取验证信息失败', 'error');
            btn.disabled = false;
            btn.textContent = '登录';
            return;
        }
        
        const capData = capR.data;
        
        let gee_validate = '';
        let seccode = '';
        
        try {
            const geeResult = await showGeeTest(capData.gt, capData.challenge);
            gee_validate = geeResult.validate;
            seccode = geeResult.seccode;
        } catch (e) {
            toast('验证取消', 'info');
            btn.disabled = false;
            btn.textContent = '登录';
            return;
        }
        
        const loginR = await API.post('/api/auth/bh3_bili/login', {
            account: account,
            password: password,
            gt_user_id: capData.gt_user_id || '',
            challenge: capData.challenge || '',
            gee_validate: gee_validate,
            seccode: seccode
        });
        
        if (loginR.retcode === 0) {
            toast('登录成功！崩坏3B服账号已保存', 'success');
            document.getElementById('bh3Account').value = '';
            document.getElementById('bh3Password').value = '';
        } else {
            toast(loginR.message || '登录失败', 'error');
        }
    } catch (e) {
        toast('网络错误', 'error');
    }
    
    btn.disabled = false;
    btn.textContent = '登录';
});

// ============ 账号加载辅助 ============
async function loadAccountSelects() {
    try {
        const r = await API.get('/api/accounts');
        const accounts = r.data || [];
        const options = accounts.map(a => `<option value="${a.id}">${a.name} (${a.uid})</option>`).join('');
        const html = '<option value="">-- 选择账号 --</option>' + options;
        
        const screenSel = document.getElementById('screenAccountSelect');
        const liveSel = document.getElementById('liveAccountSelect');
        if (screenSel) screenSel.innerHTML = html;
        if (liveSel) liveSel.innerHTML = html;
    } catch (e) {}
}

// ============ 屏幕扫码 ============
let screenStream = null;
let screenWs = null;
let screenInterval = null;
const screenCanvas = document.getElementById('screenCanvas');
const screenCtx = screenCanvas.getContext('2d');

document.getElementById('screenStartBtn').addEventListener('click', startScreenScan);
document.getElementById('screenStopBtn').addEventListener('click', stopScreenScan);

async function startScreenScan() {
    const accountId = document.getElementById('screenAccountSelect').value;
    const game = document.getElementById('screenGameSelect').value;
    
    if (!accountId) {
        toast('请先选择账号', 'error');
        return;
    }

    updateSetting('last_account', accountId);
    updateSetting('last_game', game);
    
    try {
        screenStream = await navigator.mediaDevices.getDisplayMedia({
            video: { width: 640, height: 360, frameRate: 5 }
        });
        
        const video = document.getElementById('screenPreview');
        const placeholder = document.getElementById('screenPlaceholder');
        video.srcObject = screenStream;
        video.style.display = 'block';
        placeholder.style.display = 'none';
        
        document.getElementById('screenStartBtn').style.display = 'none';
        document.getElementById('screenStopBtn').style.display = 'inline-block';
        
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        screenWs = new WebSocket(`${protocol}//${location.host}/ws/screen_scan`);
        
        screenWs.onopen = () => {
            document.getElementById('screenStatus').textContent = '正在监视屏幕...';
            toast('屏幕监视已启动', 'success');
        };
        
        screenWs.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (data.type === 'qr_detected') {
                handleDetectedQR(data.data, accountId, game, 'screenResult');
            }
        };
        
        screenWs.onclose = () => {
            if (screenInterval) stopScreenScan();
        };
        
        video.play();
        await new Promise(r => setTimeout(r, 800));
        
        screenInterval = setInterval(() => {
            if (video.readyState >= 2) {
                const w = 640;
                const h = 360;
                screenCanvas.width = w;
                screenCanvas.height = h;
                screenCtx.drawImage(video, 0, 0, w, h);
                const frameData = screenCtx.getImageData(0, 0, w, h).data;
                const header = new Uint8Array(4);
                header[0] = (w >> 8) & 0xff;
                header[1] = w & 0xff;
                header[2] = (h >> 8) & 0xff;
                header[3] = h & 0xff;
                
                const full = new Uint8Array(4 + frameData.length);
                full.set(header, 0);
                full.set(frameData, 4);
                
                if (screenWs && screenWs.readyState === WebSocket.OPEN) {
                    screenWs.send(full);
                }
            }
        }, 200);
        
    } catch (e) {
        toast('屏幕共享失败或被拒绝', 'error');
        stopScreenScan();
    }
}

function stopScreenScan() {
    if (screenInterval) {
        clearInterval(screenInterval);
        screenInterval = null;
    }
    if (screenWs) {
        screenWs.close();
        screenWs = null;
    }
    if (screenStream) {
        screenStream.getTracks().forEach(t => t.stop());
        screenStream = null;
    }
    
    document.getElementById('screenPreview').style.display = 'none';
    document.getElementById('screenCanvas').style.display = 'none';
    document.getElementById('screenPlaceholder').style.display = 'flex';
    document.getElementById('screenStartBtn').style.display = 'inline-block';
    document.getElementById('screenStopBtn').style.display = 'none';
    document.getElementById('screenStatus').textContent = '已停止';
}

// ============ 直播扫码 ============
let liveWs = null;

document.getElementById('liveStartBtn').addEventListener('click', startLiveScan);
document.getElementById('liveStopBtn').addEventListener('click', stopLiveScan);

function startLiveScan() {
    const platform = document.getElementById('livePlatform').value;
    const roomId = document.getElementById('liveRoomId').value.trim();
    const accountId = document.getElementById('liveAccountSelect').value;
    const game = document.getElementById('liveGameSelect').value;

    updateSetting('last_account', accountId);
    updateSetting('last_game', game);
    updateSetting('last_live_platform', platform);
    updateSetting('last_live_room_id', roomId);
    
    if (!roomId) {
        toast('请输入直播间RID', 'error');
        return;
    }
    if (!accountId) {
        toast('请先选择账号', 'error');
        return;
    }
    if (!/^\d+$/.test(roomId)) {
        toast('RID必须是纯数字', 'error');
        return;
    }
    
    document.getElementById('liveStartBtn').style.display = 'none';
    document.getElementById('liveStopBtn').style.display = 'inline-block';
    document.getElementById('liveStatus').textContent = '正在连接直播流...';
    document.getElementById('liveResult').innerHTML = '';
    document.getElementById('liveResult').style.display = 'none';
    
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    liveWs = new WebSocket(`${protocol}//${location.host}/ws/live_scan`);
    
    liveWs.onopen = () => {
        liveWs.send(JSON.stringify({
            action: 'start',
            platform: platform,
            room_id: roomId
        }));
    };
    
    liveWs.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === 'status') {
            document.getElementById('liveStatus').textContent = data.message || data.status;
        } else if (data.type === 'error') {
            document.getElementById('liveStatus').textContent = '错误: ' + data.data;
            toast(data.data, 'error');
        } else if (data.type === 'qr_detected') {
            handleDetectedQR(data.data, accountId, game, 'liveResult');
        }
    };
    
    liveWs.onclose = () => {
        stopLiveScan();
    };
    
    liveWs.onerror = () => {
        document.getElementById('liveStatus').textContent = '连接错误';
    };
}

function stopLiveScan() {
    if (liveWs && liveWs.readyState === WebSocket.OPEN) {
        liveWs.send(JSON.stringify({ action: 'stop' }));
        liveWs.close();
    }
    liveWs = null;
    document.getElementById('liveStartBtn').style.display = 'inline-block';
    document.getElementById('liveStopBtn').style.display = 'none';
    document.getElementById('liveStatus').textContent = '已停止';
}

// ============ 通用：处理检测到的二维码并尝试登录 ============
function detectGameFromQR(qrText) {
    if (qrText.includes('/hk4e_cn/') || qrText.includes('hk4e-sdk')) return 'hk4e';
    if (qrText.includes('/hkrpg_cn/')) return 'hkrpg';
    if (qrText.includes('/bh3_cn/')) return 'bh3';
    if (qrText.includes('/nap_cn/')) return 'nap';
    // 通过 app_id 检测
    const appMatch = qrText.match(/app_id=(\d+)/);
    if (appMatch) {
        const map = {'1': 'bh3', '4': 'hk4e', '8': 'hkrpg', '12': 'nap'};
        if (map[appMatch[1]]) return map[appMatch[1]];
    }
    return 'hk4e';
}

async function handleDetectedQR(qrText, accountId, game, resultDivId) {
    const resultDiv = document.getElementById(resultDivId);
    resultDiv.style.display = 'block';
    
    const now = new Date().toLocaleTimeString();

    // 从QR码URL自动检测游戏类型
    const detectedGame = detectGameFromQR(qrText);
    if (detectedGame !== game) {
        game = detectedGame;
    }

    const item = document.createElement('div');
    item.className = 'result-item';
    item.innerHTML = `<span class="time">${now}</span> 检测到[${game}]: ${qrText.substring(0, 50)}...`;
    resultDiv.appendChild(item);
    
    // 提取ticket: 支持 ticket=xxx 和 biz_key=xxx 两种格式
    let ticket = '';
    const match = qrText.match(/[?&]ticket=([^&#\s]+)/);
    if (match) {
        ticket = decodeURIComponent(match[1]);
    } else {
        const bizMatch = qrText.match(/[?&]biz_key=([^&#\s]+)/);
        if (bizMatch) {
            ticket = decodeURIComponent(bizMatch[1]);
        }
    }
    
    if (!ticket) {
        item.className += ' error';
        item.innerHTML = `<span class="time">${now}</span> 无法提取ticket: ${qrText.substring(0, 30)}...`;
        toast('无法解析二维码中的ticket', 'error');
        return;
    }
    
    try {
        const r = await API.post('/api/scan/game', {
            account_id: parseInt(accountId),
            game: game,
            ticket: ticket
        });
        
        if (r.retcode === 0) {
            item.className += ' success';
            item.innerHTML = `<span class="time">${now}</span> OK ${r.message}`;
            toast(r.message, 'success');

            try {
                const cfg = await API.get('/api/config');
                if (cfg.auto_exit) {
                    setTimeout(() => {
                        if (resultDivId === 'screenResult') stopScreenScan();
                        else stopLiveScan();
                    }, 500);
                }
            } catch (e) {}
        } else {
            item.className += ' error';
            item.innerHTML = `<span class="time">${now}</span> X ${r.message}`;
        }
    } catch (e) {
        item.className += ' error';
        item.innerHTML = `<span class="time">${now}</span> X 请求失败`;
    }
    
    resultDiv.scrollTop = resultDiv.scrollHeight;
}

// ============ 系统设置 ============
async function loadSettings() {
    try {
        const r = await API.get('/api/config');
        document.getElementById('cfgAutoStart').checked = !!r.auto_start;
        document.getElementById('cfgAutoExit').checked = !!r.auto_exit;
        document.getElementById('cfgAutoLogin').checked = !!r.auto_login;
    } catch (e) {}
}

async function updateSetting(key, value) {
    try {
        await API.put(`/api/config/${key}?value=${value}`);
    } catch (e) {}
}

document.getElementById('cfgAutoStart').addEventListener('change', (e) => {
    updateSetting('auto_start', e.target.checked);
});

document.getElementById('cfgAutoExit').addEventListener('change', (e) => {
    updateSetting('auto_exit', e.target.checked);
});

document.getElementById('cfgAutoLogin').addEventListener('change', (e) => {
    updateSetting('auto_login', e.target.checked);
});

async function loadLastSettings(page) {
    try {
        const r = await API.get('/api/config');
        if (r.last_account) {
            const sel = page === 'screen' ? document.getElementById('screenAccountSelect') : document.getElementById('liveAccountSelect');
            if (sel && sel.querySelector(`option[value="${r.last_account}"]`)) {
                sel.value = r.last_account;
            }
        }
        if (page === 'screen' && r.last_game) {
            const sel = document.getElementById('screenGameSelect');
            if (sel && sel.querySelector(`option[value="${r.last_game}"]`)) {
                sel.value = r.last_game;
            }
        }
        if (page === 'live') {
            if (r.last_live_platform) document.getElementById('livePlatform').value = r.last_live_platform;
            if (r.last_live_room_id) document.getElementById('liveRoomId').value = r.last_live_room_id;
            if (r.last_game) document.getElementById('liveGameSelect').value = r.last_game;
        }
        if (r.auto_start && page === 'screen') {
            startScreenScan();
        }
    } catch (e) {}
}

// ============ 账号管理 ============
document.getElementById('addAccountBtn').addEventListener('click', () => {
    document.getElementById('page-login').classList.add('active');
    document.getElementById('page-accounts').classList.remove('active');
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector('[data-page="login"]').classList.add('active');
});

async function loadAccounts() {
    try {
        const r = await API.get('/api/accounts');
        const tbody = document.getElementById('accountsTbody');
        
        if (!r.data || r.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty">暂无账号，请先在"扫码登录"页面添加</td></tr>';
            return;
        }
        
        tbody.innerHTML = r.data.map(a => `
            <tr data-id="${a.id}">
                <td>${a.id}</td>
                <td>${escapeHtml(a.name)}</td>
                <td>${escapeHtml(a.uid)}</td>
                <td>${escapeHtml(a.server)}</td>
                <td class="note-cell" data-id="${a.id}" onclick="editNote(event, '${escapeHtml(a.note || '')}')">${escapeHtml(a.note || '双击编辑')}</td>
                <td>${a.created_at || '-'}</td>
                <td>
                    <div class="action-btns">
                        <button class="btn btn-sm btn-outline" onclick="setDefaultAccount(${a.id})">默认</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteAccount(${a.id})">删除</button>
                    </div>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        toast('加载账号失败', 'error');
    }
}

function editNote(e, currentNote) {
    const td = e.target;
    if (td.querySelector('input')) return;
    
    const accountId = td.dataset.id;
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'note-input';
    input.value = currentNote === '双击编辑' ? '' : currentNote;
    
    td.textContent = '';
    td.appendChild(input);
    input.focus();
    
    input.addEventListener('blur', async () => {
        const newNote = input.value.trim();
        await API.put(`/api/accounts/${accountId}`, { note: newNote });
        td.textContent = newNote || '双击编辑';
    });
    
    input.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter') input.blur();
        if (ev.key === 'Escape') {
            td.textContent = currentNote || '双击编辑';
        }
    });
}

async function deleteAccount(id) {
    if (!confirm(`确定删除账号 #${id}？`)) return;
    
    try {
        const r = await API.del(`/api/accounts/${id}`);
        if (r.retcode === 0) {
            toast('删除成功', 'success');
            loadAccounts();
            loadAccountSelects();
        }
    } catch (e) {
        toast('删除失败', 'error');
    }
}

async function setDefaultAccount(id) {
    await updateSetting('last_account', id);
    toast('已设为默认账号', 'success');
    loadAccounts();
}

// ============ 右键菜单 ============
let contextMenuRow = null;
const contextMenu = document.getElementById('contextMenu');

document.getElementById('accountsTbody').addEventListener('contextmenu', (e) => {
    const tr = e.target.closest('tr');
    if (!tr || !tr.dataset.id) return;
    
    e.preventDefault();
    contextMenuRow = tr.dataset.id;
    contextMenu.style.display = 'block';
    contextMenu.style.left = e.pageX + 'px';
    contextMenu.style.top = e.pageY + 'px';
});

document.addEventListener('click', () => {
    contextMenu.style.display = 'none';
});

contextMenu.addEventListener('click', (e) => {
    const action = e.target.dataset.action;
    if (!action || !contextMenuRow) return;
    
    const row = document.querySelector(`tr[data-id="${contextMenuRow}"]`);
    const cells = row ? row.querySelectorAll('td') : [];
    
    if (action === 'copy-uid') {
        const uid = cells[2] ? cells[2].textContent : '';
        navigator.clipboard.writeText(uid).then(() => toast('UID已复制', 'success'));
    } else if (action === 'delete') {
        deleteAccount(contextMenuRow);
    }
    contextMenu.style.display = 'none';
});

function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

// ============ 初始化 ============
loadAccounts();
loadAccountSelects();
