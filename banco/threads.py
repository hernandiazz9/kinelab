import glob,time,numpy as np,onnxruntime as ort
base='${KINELAB_BENCH_DIR:-./banco/}models/'
for key in ['rtmpose-s','rtmpose-m']:
    p=[q for q in glob.glob(base+'**/end2end.onnx',recursive=True) if key in q][0]
    for th in [1,2,4,5,6,8,11]:
        so=ort.SessionOptions(); so.log_severity_level=3; so.intra_op_num_threads=th
        s=ort.InferenceSession(p,so,providers=['CPUExecutionProvider']); n=s.get_inputs()[0].name
        x=np.random.randn(1,3,256,192).astype(np.float32)
        for _ in range(8): s.run(None,{n:x})
        t=[]
        for _ in range(40):
            a=time.perf_counter(); s.run(None,{n:x}); t.append((time.perf_counter()-a)*1000)
        t=np.array(t); print(f"{key} threads={th:2d} min={t.min():7.2f} p50={np.median(t):7.2f} mean={t.mean():7.2f} ms")
