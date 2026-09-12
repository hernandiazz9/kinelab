import glob,time,numpy as np,onnxruntime as ort
base='${KINELAB_BENCH_DIR:-./banco/}models/'
p=[q for q in glob.glob(base+'**/end2end.onnx',recursive=True) if 'rtmpose-m' in q][0]
for opts in [{}, {'MLComputeUnits':'CPUAndGPU'}, {'MLComputeUnits':'CPUAndNeuralEngine'}, {'MLComputeUnits':'CPUOnly'},
             {'ModelFormat':'MLProgram','MLComputeUnits':'ALL'}, {'ModelFormat':'MLProgram','MLComputeUnits':'CPUAndNeuralEngine'}]:
    try:
        so=ort.SessionOptions(); so.log_severity_level=3
        t0=time.time(); s=ort.InferenceSession(p,so,providers=['CoreMLExecutionProvider'],provider_options=[opts]); load=time.time()-t0
        n=s.get_inputs()[0].name; x=np.random.randn(1,3,256,192).astype(np.float32)
        for _ in range(8): s.run(None,{n:x})
        t=[]
        for _ in range(40):
            a=time.perf_counter(); s.run(None,{n:x}); t.append((time.perf_counter()-a)*1000)
        o=s.run(None,{n:x}); nan=int(np.isnan(o[0]).sum())
        print(f"{str(opts):70s} min={min(t):6.2f} p50={np.median(t):6.2f}ms load={load:4.1f}s nan={nan}")
    except Exception as e:
        print(f"{str(opts):70s} ERROR {type(e).__name__}: {str(e)[:110]}")
