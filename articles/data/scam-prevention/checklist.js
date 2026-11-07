'use strict';
(() => {
  const box = document.querySelector('#risk-checklist');
  const status = document.querySelector('#checklist-status');
  const reset = document.querySelector('#checklist-reset');
  if (!box || !status || !reset) return;
  const items = Array.from(box.querySelectorAll('input[type="checkbox"]'));
  const update = () => {
    status.textContent = items.some(item => item.checked)
      ? '該当する項目があります。送金・接続・署名をいったん止め、状況別の初動対応を確認してください。選択の数で詐欺を確定するものではありません。'
      : '未選択でも安全とは判断できません。これは確認用のメモで、詐欺の判定や安全の保証ではありません。';
  };
  box.addEventListener('change', update);
  reset.addEventListener('click', () => { items.forEach(item => { item.checked = false; }); update(); });
  update();
})();
