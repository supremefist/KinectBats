using System;
using System.Collections.Generic;
using System.Linq;
using System.Diagnostics;

using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Audio;
using Microsoft.Xna.Framework.Content;
using Microsoft.Xna.Framework.GamerServices;
using Microsoft.Xna.Framework.Graphics;
using Microsoft.Xna.Framework.Input;
using Microsoft.Xna.Framework.Media;

using FarseerPhysics;
using FarseerPhysics.Dynamics;
using FarseerPhysics.Factories;
using FarseerPhysics.Common;

using Microsoft.Kinect;

namespace KinectBats
{
    /// <summary>
    /// This is the main type for your game
    /// </summary>
    public class KinectBats : Game
    {
        World world;
        Body leftBody;
        Vertices leftBodyVertices;

        GraphicsDeviceManager graphics;
        SpriteBatch spriteBatch;
        KinectSensor kinect;
        Texture2D colorVideo, depthVideo;
        Boolean debugging = true;
        Boolean done = false;
        const int skeletonCount = 6;
        Skeleton[] allSkeletons = new Skeleton[skeletonCount];
        CoordinateMapper cm;

        Texture2D marker;
        Texture2D marker2;
        Texture2D pixel;

        ColorImagePoint leftHandPoint;
        ColorImagePoint leftElbowPoint;
        bool leftTracked = false;

        ColorImagePoint rightHandPoint;
        ColorImagePoint rightElbowPoint;
        bool rightTracked = false;

        Line l;

        const DepthImageFormat depthFormat = DepthImageFormat.Resolution320x240Fps30;
        const ColorImageFormat colorFormat = ColorImageFormat.RgbResolution640x480Fps30;

        VertexPositionColor[] vertices;
        BasicEffect basicEffect;

        public KinectBats()
        {
            graphics = new GraphicsDeviceManager(this);
            Content.RootDirectory = "Content";
        }

        /// <summary>
        /// Allows the game to perform any initialization it needs to before starting to run.
        /// This is where it can query for any required services and load any non-graphic
        /// related content.  Calling base.Initialize will enumerate through any components
        /// and initialize them as well.
        /// </summary>
        protected override void Initialize()
        {

            // 1 meter = 64 pixels
            ConvertUnits.SetDisplayUnitToSimUnitRatio(64f);

            try
            {
                if (KinectSensor.KinectSensors.Count > 0)
                {
                    //Initialise Kinect
                    kinect = KinectSensor.KinectSensors[0];

                    if (kinect.Status == KinectStatus.Connected)
                    {
                        kinect.ColorStream.Enable(colorFormat);
                        kinect.DepthStream.Enable(depthFormat);
                        kinect.SkeletonStream.Enable();

                        kinect.AllFramesReady += new EventHandler<AllFramesReadyEventArgs>(kinect_AllFramesReady);

                        kinect.Start();

                        cm = new CoordinateMapper(kinect);
                        Debug.WriteLineIf(debugging, kinect.Status);
                    }

                    
                }
            }
            catch (Exception e)
            {
                Debug.WriteLine(e.ToString());
            }

            base.Initialize();

            //l = new Line(new Vector2(0, 0), new Vector2(100, 100), 20, Color.Black, pixel);
        }

        Skeleton[] GetPlayerSkeletons(AllFramesReadyEventArgs e)
        {
            using (SkeletonFrame frame = e.OpenSkeletonFrame())
            {
                Skeleton[] trackedSkeletons = new Skeleton[2];

                if (frame == null)
                {
                    return trackedSkeletons;
                }

                frame.CopySkeletonDataTo(allSkeletons);

                //(Skeleton[])(from s in allSkeletons where s.TrackingState == SkeletonTrackingState.Tracked);
                var firstFound = false;

                for (int i = 0; i < skeletonCount; i++)
                {
                    if (allSkeletons[i].TrackingState == SkeletonTrackingState.Tracked)
                    {
                        if (!firstFound)
                        {
                            trackedSkeletons[0] = allSkeletons[i];
                            firstFound = true;
                        }
                        else
                        {
                            trackedSkeletons[1] = allSkeletons[i];
                        }
                    }
                }

                return trackedSkeletons;
            }
        }

        private byte[] ConvertDepthFrame(short[] depthFrame, DepthImageStream depthStream)
        {
            int RedIndex = 0, GreenIndex = 1, BlueIndex = 2, AlphaIndex = 3;

            byte[] depthFrame32 = new byte[depthStream.FrameWidth * depthStream.FrameHeight * 4];

            for (int i16 = 0, i32 = 0; i16 < depthFrame.Length && i32 < depthFrame32.Length; i16++, i32 += 4)
            {
                int player = depthFrame[i16] & DepthImageFrame.PlayerIndexBitmask;
                int realDepth = depthFrame[i16] >> DepthImageFrame.PlayerIndexBitmaskWidth;

                // transform 13-bit depth information into an 8-bit intensity appropriate
                // for display (we disregard information in most significant bit)
                byte intensity = (byte)(~(realDepth >> 4));

                depthFrame32[i32 + RedIndex] = (byte)(intensity);
                depthFrame32[i32 + GreenIndex] = (byte)(intensity);
                depthFrame32[i32 + BlueIndex] = (byte)(intensity);
                depthFrame32[i32 + AlphaIndex] = 255;
            }
            return depthFrame32;
        }

        void kinect_AllFramesReady(object sender, AllFramesReadyEventArgs imageFrames)
        {
            if (done)
            {
                return;
            }

            kinect_ColorFrameReady(sender, imageFrames);
            Skeleton[] skeletons = GetPlayerSkeletons(imageFrames);

            if (skeletons[0] != null)
            {
                UpdateSkeleton(skeletons[0], imageFrames, 0);
            }
            else
            {
                leftTracked = false;
            }

            if (skeletons[1] != null)
            {
                UpdateSkeleton(skeletons[1], imageFrames, 1);
            }
            else
            {
                rightTracked = false;
            }
        }

        void kinect_ColorFrameReady(object sender, AllFramesReadyEventArgs imageFrames)
        {
            //Get raw image
            ColorImageFrame colorVideoFrame = imageFrames.OpenColorImageFrame();

            if (colorVideoFrame != null)
            {
                //Create array for pixel data and copy it from the image frame
                Byte[] pixelData = new Byte[colorVideoFrame.PixelDataLength];
                colorVideoFrame.CopyPixelDataTo(pixelData);

                //Convert RGBA to BGRA
                Byte[] bgraPixelData = new Byte[colorVideoFrame.PixelDataLength];
                for (int i = 0; i < pixelData.Length; i += 4)
                {
                    bgraPixelData[i] = pixelData[i + 2];
                    bgraPixelData[i + 1] = pixelData[i + 1];
                    bgraPixelData[i + 2] = pixelData[i];
                    bgraPixelData[i + 3] = (Byte)255; //The video comes with 0 alpha so it is transparent
                }

                // Create a texture and assign the realigned pixels
                colorVideo = new Texture2D(graphics.GraphicsDevice, colorVideoFrame.Width, colorVideoFrame.Height);
                colorVideo.SetData(bgraPixelData);

                colorVideoFrame.Dispose();
            }

            
        }

        void UpdateSkeleton(Skeleton s, AllFramesReadyEventArgs e, int index)
        {
            using (DepthImageFrame depth = e.OpenDepthImageFrame())
            {
                if (depth == null || kinect == null)
                {
                    return;
                }

                bool tracked = true;
                if ((s.Joints[JointType.HandLeft].TrackingState != JointTrackingState.Tracked) || (s.Joints[JointType.HandLeft].TrackingState != JointTrackingState.Tracked))
                {
                    tracked = false;
                    Console.WriteLine(tracked);
                    
                }

                DepthImagePoint leftHandDepthPoint = cm.MapSkeletonPointToDepthPoint(s.Joints[JointType.HandLeft].Position, depthFormat);
                DepthImagePoint leftElbowDepthPoint = cm.MapSkeletonPointToDepthPoint(s.Joints[JointType.ElbowLeft].Position, depthFormat);

                if (index == 0)
                {
                    leftHandPoint = cm.MapDepthPointToColorPoint(depthFormat, leftHandDepthPoint, colorFormat);
                    leftElbowPoint = cm.MapDepthPointToColorPoint(depthFormat, leftElbowDepthPoint, colorFormat);
                    leftTracked = tracked;
                }
                else {
                    rightHandPoint = cm.MapDepthPointToColorPoint(depthFormat, leftHandDepthPoint, colorFormat);
                    rightElbowPoint = cm.MapDepthPointToColorPoint(depthFormat, leftElbowDepthPoint, colorFormat);
                    rightTracked = tracked;
                }
            }
        }

        /// <summary>
        /// LoadContent will be called once per game and is the place to load
        /// all of your content.
        /// </summary>
        protected override void LoadContent()
        {
            // Create a new SpriteBatch, which can be used to draw textures.
            spriteBatch = new SpriteBatch(GraphicsDevice);

            // TODO: use this.Content to load your game content here
            pixel = this.Content.Load<Texture2D>("pixel");
            marker = this.Content.Load<Texture2D>("marker");
            marker2 = this.Content.Load<Texture2D>("marker2");

            world = new World(new Vector2(0, 10f));

            leftBodyVertices = PolygonTools.CreateRectangle(ConvertUnits.ToSimUnits(100), ConvertUnits.ToSimUnits(20));
            leftBody = BodyFactory.CreatePolygon(world, leftBodyVertices, 1f);
            
            //leftBody = BodyFactory.CreateRectangle(world, ConvertUnits.ToSimUnits(100), ConvertUnits.ToSimUnits(20), 1f);
            leftBody.BodyType = BodyType.Dynamic;
            leftBody.Position = new Vector2(ConvertUnits.ToSimUnits(100), ConvertUnits.ToSimUnits(100));
        }

        /// <summary>
        /// UnloadContent will be called once per game and is the place to unload
        /// all content.
        /// </summary>
        protected override void UnloadContent()
        {
            // TODO: Unload any non ContentManager content here
        }

        /// <summary>
        /// Allows the game to run logic such as updating the world,
        /// checking for collisions, gathering input, and playing audio.
        /// </summary>
        /// <param name="gameTime">Provides a snapshot of timing values.</param>
        protected override void Update(GameTime gameTime)
        {
            // Allows the game to exit
            if ((Keyboard.GetState(PlayerIndex.One).IsKeyDown(Keys.Escape)) || (GamePad.GetState(PlayerIndex.One).Buttons.Back == ButtonState.Pressed))
                this.Exit();

            // variable time step but never less then 30 Hz
            world.Step(Math.Min((float)gameTime.ElapsedGameTime.TotalSeconds, (1f / 30f)));

            //l.Update(gameTime);

            base.Update(gameTime);


        }

        /// <summary>
        /// This is called when the game should draw itself.
        /// </summary>
        /// <param name="gameTime">Provides a snapshot of timing values.</param>
        protected override void Draw(GameTime gameTime)
        {
            GraphicsDevice.Clear(Color.CornflowerBlue);

            spriteBatch.Begin();

            // Draw RGB video
            if (colorVideo != null)
            {
                spriteBatch.Draw(colorVideo, new Rectangle(0, 0, 640, 480), Color.White);
            }

            if (leftTracked)
            {
                l.p1.X = leftHandPoint.X;
                l.p1.Y = leftHandPoint.Y;
                l.p2.X = leftElbowPoint.X;
                l.p2.Y = leftElbowPoint.Y;
                l.Draw(spriteBatch);

                spriteBatch.Draw(marker, new Rectangle(leftHandPoint.X - 16, leftHandPoint.Y - 16, 32, 32), Color.White);
                spriteBatch.Draw(marker, new Rectangle(leftElbowPoint.X - 16, leftElbowPoint.Y - 16, 32, 32), Color.White);
            }
            else
            {
                Console.WriteLine("Going:");
                for (int i = 0; i < leftBodyVertices.Count; i++)
                {
                    Console.WriteLine(leftBodyVertices[i].X + ", " + leftBodyVertices[i].Y);
                }

                
                Line currentLine = new Line(new Vector2(0, 0), new Vector2(ConvertUnits.ToDisplayUnits(leftBody.Position.X), ConvertUnits.ToDisplayUnits(leftBody.Position.Y)), 20, Color.Black, pixel);

                currentLine.Update(gameTime);

                currentLine.p1.X = 50;
                currentLine.p1.Y = 50;
                currentLine.p2.X = 150;
                currentLine.p2.Y = 150;
                currentLine.Draw(spriteBatch);
            }

            if (rightTracked)
            {
                spriteBatch.Draw(marker2, new Rectangle(rightHandPoint.X - 16, rightHandPoint.Y - 16, 32, 32), Color.White);
                spriteBatch.Draw(marker2, new Rectangle(rightElbowPoint.X - 16, rightElbowPoint.Y - 16, 32, 32), Color.White);
            }

            spriteBatch.End();

            base.Draw(gameTime);
        }

        void StopKinect(KinectSensor sensor)
        {
            if (sensor == null)
            {
                return;
            }

            if (sensor.SkeletonStream.IsEnabled)
            {
                sensor.SkeletonStream.Disable();
            }

            if (sensor.ColorStream.IsEnabled)
            {
                sensor.ColorStream.Disable();
            }

            if (sensor.DepthStream.IsEnabled)
            {
                sensor.DepthStream.Disable();
            }

            // detach event handlers
            sensor.AllFramesReady -= this.kinect_AllFramesReady;

            try
            {
                sensor.Stop();
            }
            catch (Exception e)
            {
                Debug.WriteLine("unknown Exception {0}", e.Message);
            }
        }

        protected override void OnExiting(Object sender, EventArgs args)
        {
            done = true;

            StopKinect(kinect);

            base.OnExiting(sender, args);
        }

    }
}


