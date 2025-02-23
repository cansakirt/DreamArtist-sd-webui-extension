import os
import gradio as gr
from modules import scripts, script_callbacks
import modules
from modules.ui import create_refresh_button, setup_progressbar
from modules import sd_hijack, shared
from modules.paths import script_path
from webui import wrap_gradio_gpu_call
import scripts.dream_artist as dream_artist
import argparse

gvars=argparse.Namespace()

def on_ui_train_tabs(params):
    txt2img_preview_params=params.txt2img_preview_params
    gvars.txt2img_preview_params=txt2img_preview_params

    return None

def on_ui_tabs():
    with gr.Blocks(analytics_enabled=False) as dream_artist_interface:
        with gr.Row().style(equal_height=False):
            with gr.Tabs(elem_id="da_train_tabs"):
                with gr.Tab(label="DreamArtist Create embedding"):
                    new_embedding_name = gr.Textbox(label="Name", interactive=True)
                    initialization_text = gr.Textbox(label="Initialization text", value="*", interactive=True)
                    nvpt = gr.Slider(label="Number of vectors per token", minimum=1, maximum=75, step=1, value=3, interactive=True)
                    use_negative = gr.Checkbox(label='Use negative embedding (DreamArtist)', value=True, interactive=True)
                    nvpt_neg = gr.Slider(label="Number of negative vectors per token", minimum=1, maximum=75, step=1, value=6, interactive=True)
                    overwrite_old_embedding = gr.Checkbox(value=False, label="Overwrite Old Embedding", interactive=True)

                    with gr.Row():
                        with gr.Column(scale=3):
                            gr.HTML(value="")

                        with gr.Column():
                            create_embedding = gr.Button(value="Create embedding", variant='primary', interactive=True)

                with gr.Tab(label="DreamArtist Train"):
                    gr.HTML(
                        value="<p style='margin-bottom: 0.7em'>Train an embedding or Hypernetwork; you must specify a directory with a set of 1:1 ratio images <a href=\"https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Textual-Inversion\" style=\"font-weight:bold;\">[wiki]</a></p>")
                    with gr.Row():
                        train_embedding_name = gr.Dropdown(label='Embedding', elem_id="train_embedding", interactive=True,
                                                           choices=sorted(sd_hijack.model_hijack.embedding_db.word_embeddings.keys()))
                        create_refresh_button(train_embedding_name, sd_hijack.model_hijack.embedding_db.load_textual_inversion_embeddings,
                                              lambda: {"choices": sorted(sd_hijack.model_hijack.embedding_db.word_embeddings.keys())},
                                              "refresh_train_embedding_name")
                    with gr.Row():
                        train_hypernetwork_name = gr.Dropdown(label='Hypernetwork', elem_id="train_hypernetwork",
                                                              choices=[x for x in shared.hypernetworks.keys()])
                        create_refresh_button(train_hypernetwork_name, shared.reload_hypernetworks,
                                              lambda: {"choices": sorted([x for x in shared.hypernetworks.keys()])}, "refresh_train_hypernetwork_name")
                    with gr.Row():
                        embedding_learn_rate = gr.Textbox(label='Embedding Learning rate', placeholder="Embedding Learning rate", value="0.005",
                                                          interactive=True)
                        hypernetwork_learn_rate = gr.Textbox(label='Hypernetwork Learning rate', placeholder="Hypernetwork Learning rate", value="0.00001",
                                                             interactive=True)

                    # support DreamArtist
                    gr.HTML(value='<p style="margin-bottom: 0.7em">DreamArtist</p>')
                    with gr.Row():
                        neg_train = gr.Checkbox(label='Train with DreamArtist', value=True, interactive=True)
                        rec_train = gr.Checkbox(label='Train with reconstruction', value=False, interactive=True)
                    cfg_scale = gr.Number(label='CFG scale', value=5.0, interactive=True)
                    rec_loss_w = gr.Slider(minimum=0.01, maximum=1.0, step=0.01, label="Reconstruction loss weight", value=1.0, interactive=True)
                    neg_lr_w = gr.Slider(minimum=0.2, maximum=5.0, step=0.05, label="Negative lr weight", value=1.0, interactive=True)
                    disc_path = gr.Textbox(label='Classifier path', placeholder="Path to classifier ckpt, can be empty", value="", interactive=True)

                    batch_size = gr.Number(label='Batch size', value=1, precision=0, interactive=True)
                    dataset_directory = gr.Textbox(label='Dataset directory', placeholder="Path to directory with input images", interactive=True)
                    log_directory = gr.Textbox(label='Log directory', placeholder="Path to directory where to write outputs", value="dream_artist",
                                               interactive=True)
                    template_file = gr.Textbox(label='Prompt template file',
                                               value=os.path.join(script_path, "textual_inversion_templates", "style_filewords.txt"), interactive=True)
                    training_width = gr.Slider(minimum=64, maximum=2048, step=64, label="Width", value=512, interactive=True)
                    training_height = gr.Slider(minimum=64, maximum=2048, step=64, label="Height", value=512, interactive=True)
                    steps = gr.Number(label='Max steps', value=100000, precision=0, interactive=True)
                    create_image_every = gr.Number(label='Save an image to log directory every N steps, 0 to disable', value=500, precision=0,
                                                   interactive=True)
                    save_embedding_every = gr.Number(label='Save a copy of embedding to log directory every N steps, 0 to disable', value=500, precision=0,
                                                     interactive=True)
                    save_image_with_stored_embedding = gr.Checkbox(label='Save images with embedding in PNG chunks', value=True, interactive=True)
                    preview_from_txt2img = gr.Checkbox(label='Read parameters (prompt, etc...) from txt2img tab when making previews', value=False,
                                                       interactive=True)

                    gr.HTML(value='<p style="margin-bottom: 0.7em">Experimental features (May be solve the problem of erratic training and difficult to reproduce [set EMA to 0.97])</p>')
                    with gr.Row():
                        ema_w = gr.Number(label='EMA (positive)', value=1.0, interactive=True)
                        ema_rep_step = gr.Number(label='EMA replace steps (positive)', value=25, interactive=True)
                        ema_w_neg = gr.Number(label='EMA (nagetive)', value=1.0, interactive=True)
                        ema_rep_step_neg = gr.Number(label='EMA replace steps (nagative)', value=25, interactive=True)

                    with gr.Row():
                        adam_beta1 = gr.Number(label='beta1', value=0.9, interactive=True)
                        adam_beta2 = gr.Number(label='beta2', value=0.999, interactive=True)

                    with gr.Row():
                        interrupt_training = gr.Button(value="Interrupt", interactive=True)
                        train_embedding = gr.Button(value="Train Embedding", variant='primary', interactive=True)
            with gr.Column():
                progressbar = gr.HTML(elem_id="da_progressbar")
                da_output = gr.Text(elem_id="da_output", value="", show_label=False)

                da_gallery = gr.Gallery(label='Output', show_label=False, elem_id='da_gallery').style(grid=4)
                da_preview = gr.Image(elem_id='da_preview', visible=False)
                da_progress = gr.HTML(elem_id="da_progress", value="")
                da_outcome = gr.HTML(elem_id="da_error", value="")
                setup_progressbar(progressbar, da_preview, 'da', textinfo=da_progress)

        create_embedding.click(
            fn=dream_artist.ui.create_embedding,
            inputs=[
                new_embedding_name,
                initialization_text,
                nvpt,
                overwrite_old_embedding,
                use_negative,
                nvpt_neg
            ],
            outputs=[
                train_embedding_name,
                da_output,
                da_outcome,
            ]
        )

        train_embedding.click(
            fn=wrap_gradio_gpu_call(dream_artist.ui.train_embedding, extra_outputs=[gr.update()]),
            _js="start_training_dreamartist",
            inputs=[
                train_embedding_name,
                embedding_learn_rate,
                batch_size,
                dataset_directory,
                log_directory,
                training_width,
                training_height,
                steps,
                create_image_every,
                save_embedding_every,
                template_file,
                save_image_with_stored_embedding,
                preview_from_txt2img,
                *gvars.txt2img_preview_params,
                cfg_scale,
                disc_path,
                neg_train,
                rec_train,
                rec_loss_w,
                neg_lr_w,
                ema_w,
                ema_rep_step,
                ema_w_neg,
                ema_rep_step_neg,
                adam_beta1,
                adam_beta2
            ],
            outputs=[
                da_output,
                da_outcome,
            ]
        )

        interrupt_training.click(
            fn=lambda: shared.state.interrupt(),
            inputs=[],
            outputs=[],
        )

    return [(dream_artist_interface, "DreamArtist", "dream_artist")]


script_callbacks.on_ui_train_tabs(on_ui_train_tabs)
script_callbacks.on_ui_tabs(on_ui_tabs)