#!/usr/bin/env python
# coding: utf-8

# In[1]:
File "/mount/src/cut-off-app/cutoff_app_v2.py", line 248, in <module>
    cutoffs['QS report score'] = cutoff_input(
                                 ~~~~~~~~~~~~^
        "QS Report",
        ^^^^^^^^^^^^
        'QS report score', 0.0, 45.0,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        safe_quantile(df['QS report score'], 0.75, 30.0)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
File "/mount/src/cut-off-app/cutoff_app_v2.py", line 223, in cutoff_input
    number_val = st.number_input("", min_value=min_val, max_value=max_val,
                               value=slider_val, step=0.5,
                               key=f"number_{col}", format="%.1f")
File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/runtime/metrics_util.py", line 532, in wrapped_func
    result = non_optional_func(*args, **kwargs)
File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/elements/widgets/number_input.py", line 448, in number_input
    return self._number_input(
           ~~~~~~~~~~~~~~~~~~^
        label=label,
        ^^^^^^^^^^^^
    ...<16 lines>...
        ctx=ctx,
        ^^^^^^^^
    )
    ^
File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/elements/widgets/number_input.py", line 594, in _number_input
    raise StreamlitValueAboveMaxError(value=value, max_value=max_value)
# In[ ]:




