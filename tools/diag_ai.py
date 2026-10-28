"""ONNX 임베딩이 sentence-transformers와 다른 이유 찾기 (Actions에서 실행)."""
import os, numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer
from transformers import AutoTokenizer
from sentence_transformers import SentenceTransformer

def log(m):
    print(m); print("::notice::" + str(m)[:3000]) if os.environ.get("GITHUB_ACTIONS") else None

texts = ["피부 재생 크림", "탈모에 좋은 차", "촉촉한 보습 로션", "아이 키 크는 젤리 먹고 10센치 컸어요"]
st = SentenceTransformer("jhgan/ko-sroberta-multitask")
log(f"ST 모듈: {[type(m).__name__ for m in st]} · max_seq {st.max_seq_length} · pooling {st[1].get_pooling_mode_str() if hasattr(st[1], 'get_pooling_mode_str') else st[1]}")
ref = st.encode(texts, normalize_embeddings=True)
hf = AutoTokenizer.from_pretrained("jhgan/ko-sroberta-multitask")
tk = Tokenizer.from_file("/tmp/onnx/tokenizer.json")
for t in texts[:2]:
    log(f"토큰 비교 '{t}': HF {hf(t)['input_ids']} · tokenizers {tk.encode(t).ids}")
s = ort.InferenceSession("/tmp/onnx/model.onnx")
log(f"ONNX 입력 {[(i.name, i.shape) for i in s.get_inputs()]} · 출력 {[(o.name, o.shape) for o in s.get_outputs()]}")
enc = hf(texts, padding=True, return_tensors="np")
feed = {k: v.astype(np.int64) for k, v in enc.items() if k in {i.name for i in s.get_inputs()}}
outs = s.run(None, feed)
for o, v in zip(s.get_outputs(), outs): log(f"출력 {o.name} 모양 {v.shape}")
h = outs[0]; m = enc["attention_mask"][..., None]
v = (h * m).sum(1) / m.sum(1); v /= np.linalg.norm(v, axis=1, keepdims=True)
log(f"HF 토크나이저+ONNX 평균풀링 vs ST 코사인: {np.round((ref * v).sum(1), 4).tolist()}")
# ST 내부 토큰 임베딩과 ONNX 비교
fe = st.encode(texts, output_value="token_embeddings")
log(f"ST 토큰 임베딩 첫 문장 [0,:3] {np.round(fe[0][0][:3].cpu().numpy() if hasattr(fe[0], 'cpu') else fe[0][0][:3], 4).tolist()} · ONNX {np.round(h[0][0][:3], 4).tolist()}")
log(f"feed 키 {list(feed)} · token_type_ids 있음 {'token_type_ids' in enc}")
